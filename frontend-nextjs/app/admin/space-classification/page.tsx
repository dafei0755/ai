'use client';

import { FormEvent, useEffect, useState } from 'react';
import axios from 'axios';
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Network,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  XCircle,
} from 'lucide-react';

interface RegistryHealth {
  schema_version: string;
  status: string;
  summary: Record<string, number>;
  issues: Record<string, string[]>;
}

interface SubdomainHealth {
  schema_version: string;
  status: string;
  summary: Record<string, number>;
  issues: Record<string, string[]>;
}

interface SubdomainRecord {
  subdomain_id: string;
  name_cn: string;
  name_en: string;
  parent_project_type_id?: string;
  parent_project_type_name?: string;
  ontology_framework_id?: string;
  activation_pack_id?: string;
  activation_pack_loaded?: boolean;
  routing_binding_matched?: boolean;
  has_runtime_detector_binding?: boolean;
  has_yaml_registry_binding?: boolean;
  has_master_index_pack_mapping?: boolean;
  status?: string;
  review_status?: string;
  owner?: string;
  signal_keywords?: string[];
  specialty_tag_assist?: string[];
  aliases?: string[];
  knowledge_package_ids?: string[];
}

interface ActivationPackCoordination {
  schema_version?: string;
  mode?: string;
  primary_pack_id?: string;
  secondary_pack_ids?: string[];
  loaded_pack_ids?: string[];
  merge_policy?: string;
  secondary_packs?: Array<{
    pack_id?: string;
    subdomain_id?: string;
    parent_project_type_id?: string;
    confidence?: number;
    matched_keywords?: string[];
    role?: string;
  }>;
}

interface CapabilityPlanNode {
  capability_group?: string;
  name?: string;
  status?: string;
  primary_principle?: string;
  maturity_ceiling_rule?: string;
  evidence_requirement?: string;
  blocking_missing_slots?: string[];
}

interface CapabilityPlan {
  schema_version?: string;
  registry?: {
    schema_version?: string;
    status?: string;
    path?: string;
    issues?: Array<{
      code?: string;
      message?: string;
    }>;
  };
  status?: string;
  maturity_ceiling?: string;
  output_mode?: string;
  required_disciplines?: string[];
  discipline_coverage?: string;
  capability_nodes?: CapabilityPlanNode[];
}

interface DiagnosticReport {
  schema_version: string;
  normalization_trace?: {
    schema_version?: string;
    original_text?: string;
    normalized_text?: string;
    changed?: boolean;
    fullwidth_converted?: boolean;
    replacement_count?: number;
    replacements?: Array<{
      alias: string;
      canonical: string;
      source?: string;
      start?: number;
      end?: number;
    }>;
  };
  classification_output?: {
    schema_version?: string;
    project_type_id?: string;
    ontology_framework_id?: string;
    subdomain_id?: string;
    activation_pack_id?: string;
    founding_type?: string;
    project_scale?: string;
    discipline_scope?: string[];
    lead_discipline?: string;
    hard_constraint_discipline_ids?: string[];
    project_conditions?: string[];
  };
  classification: {
    status?: string;
    project_type?: string;
    project_type_name?: string;
    confidence?: number;
    primary_bucket?: string;
  };
  binding_summary: {
    ontology_framework_id?: string;
    subdomain_id?: string;
    activation_pack_id?: string;
    secondary_activation_pack_ids?: string[];
    project_scale?: string;
    spatial_layer_ids?: string[];
    ontology_dimension_ids?: string[];
    knowledge_package_ids?: string[];
  };
  coverage_gaps: Array<{
    severity: string;
    code: string;
    message: string;
  }>;
  health: {
    severity: string;
    blocking_count: number;
    warning_count: number;
  };
  activation_pack_preview: {
    loaded: boolean;
  };
  subdomain_signals?: Array<{
    suggested_subdomain_id?: string;
    activation_pack_id?: string;
    confidence?: number;
    matched_keywords?: string[];
  }>;
  founding_type_candidates?: Array<{
    founding_type_id?: string;
    confidence?: number;
    matched_keywords?: {
      primary?: string[];
      secondary?: string[];
    };
  }>;
  activation_pack_coordination?: ActivationPackCoordination;
  capability_plan?: CapabilityPlan;
  context_packet?: {
    schema_version: string;
    classification?: {
      project_type_id?: string;
      project_scale?: string;
      founding_type_id?: string;
      subdomain?: {
        primary_subdomain_id?: string;
      };
    };
    context_vector?: Record<string, string | undefined>;
    output_mode?: {
      primary_output_mode?: string;
      user_visible_container?: string;
    };
    discipline_switch?: {
      spatial_extent_level?: string;
      required_disciplines?: string[];
      current_coverage?: string;
    };
    missing_slots?: Array<{
      name: string;
      severity?: string;
      action?: string;
      active_for_current_round?: boolean;
      deferred_by?: string;
      user_visible_note?: string;
    }>;
    activation_pack_coordination?: ActivationPackCoordination;
    ontology_binding?: {
      ontology_framework_id?: string;
      activation_pack_id?: string;
      secondary_activation_pack_ids?: string[];
      spatial_layer_ids?: string[];
      ontology_dimension_ids?: string[];
      priority_ontology_dimension_ids?: string[];
    };
    knowledge_binding?: {
      knowledge_package_ids?: string[];
      knowledge_card_weights?: Record<string, number>;
    };
  };
}

interface SpaceClassificationType {
  type_id: string;
  display_name: string;
  name_en: string;
  description: string;
  status: string;
  review_status: string;
  owner: string;
  parent_type?: string;
  ontology_framework_id?: string;
  has_type_operating_profile?: boolean;
  profile_id?: string;
  type_operating_profile?: {
    profile_id?: string;
    ontology_framework?: string;
    master_index_ontology_framework?: string;
    framework_matches_master_index?: boolean;
    required_dimensions?: string[];
    required_min_coverage?: number;
    knowledge_package_ids?: string[];
    missing_knowledge_package_ids?: string[];
    search_tags?: string[];
    active_discipline_ids?: string[];
    type_method_profile_id?: string;
    type_method_priority_sequence?: string[];
    general_method_profile_id?: string;
    general_method_check_ids?: string[];
    downstream_profiles?: Record<string, string | undefined>;
    system_target_objects?: string[];
    system_required_freeze?: string[];
    issue_codes?: string[];
  };
  priority: number;
  keyword_count: number;
  has_admin_override: boolean;
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

interface CandidateStatistics {
  pending?: { count: number; avg_confidence?: number };
  approved?: { count: number };
  rejected?: { count: number };
}

function getAuthHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('app_auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function adminApi(path: string) {
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';
  return `${base}${path}`;
}

function pillClass(value?: string) {
  if (value === 'blocking' || value === 'needs_attention') return 'bg-red-50 text-red-700 border-red-200';
  if (value === 'warning' || value === 'ambiguous' || value === 'needs_clarification') {
    return 'bg-amber-50 text-amber-700 border-amber-200';
  }
  return 'bg-emerald-50 text-emerald-700 border-emerald-200';
}

function confidenceClass(score: number) {
  if (score >= 0.8) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (score >= 0.5) return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-red-50 text-red-700 border-red-200';
}

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    user_input: '用户输入',
    crawler: '历史外部导入',
    manual: '手动录入',
  };
  return labels[source] || source;
}

function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="rounded-lg border bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value ?? 0}</p>
    </div>
  );
}

function ApproveCandidateModal({
  candidate,
  onClose,
  onDone,
}: {
  candidate: TypeCandidate;
  onClose: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
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

  const submitApproval = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      setLoading(true);
      setError('');
      await axios.post(
        adminApi(`/api/admin/project-types/candidates/${candidate.id}/approve`),
        {
          type_id: form.type_id.trim(),
          name_zh: form.name_zh.trim(),
          name_en: form.name_en.trim(),
          keywords: form.keywords.split(',').map((item) => item.trim()).filter(Boolean),
          secondary_keywords: form.secondary_keywords.split(',').map((item) => item.trim()).filter(Boolean),
          priority: form.priority,
          min_secondary_hits: form.min_secondary_hits,
          include_in_prompt: form.include_in_prompt,
          reviewer_note: form.reviewer_note,
        },
        { headers: getAuthHeaders() }
      );
      onDone();
    } catch (err: any) {
      setError(err.response?.data?.detail || '审批候选失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-xl">
        <div className="border-b px-5 py-4">
          <h3 className="text-lg font-semibold">审批空间分类候选</h3>
          <p className="mt-1 font-mono text-xs text-gray-500">{candidate.type_id_suggestion}</p>
        </div>
        <form onSubmit={submitApproval} className="space-y-4 p-5">
          <div className="rounded-lg border bg-gray-50 p-3 text-sm text-gray-600">
            <p>来源：{sourceLabel(candidate.source)}，出现 {candidate.occurrence_count} 次。</p>
            {candidate.sample_inputs[0] && <p className="mt-1 truncate">样例：{candidate.sample_inputs[0]}</p>}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label htmlFor="candidate-type-id" className="block text-sm font-medium text-gray-700">
                英文 ID
              </label>
              <input
                id="candidate-type-id"
                value={form.type_id}
                onChange={(event) => setForm({ ...form, type_id: event.target.value })}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm"
                required
              />
            </div>
            <div>
              <label htmlFor="candidate-name-zh" className="block text-sm font-medium text-gray-700">
                中文名
              </label>
              <input
                id="candidate-name-zh"
                value={form.name_zh}
                onChange={(event) => setForm({ ...form, name_zh: event.target.value })}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div>
            <label htmlFor="candidate-name-en" className="block text-sm font-medium text-gray-700">
              英文检索词
            </label>
            <input
              id="candidate-name-en"
              value={form.name_en}
              onChange={(event) => setForm({ ...form, name_en: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="candidate-keywords" className="block text-sm font-medium text-gray-700">
              主关键词
            </label>
            <textarea
              id="candidate-keywords"
              value={form.keywords}
              onChange={(event) => setForm({ ...form, keywords: event.target.value })}
              className="mt-1 min-h-20 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label htmlFor="candidate-secondary-keywords" className="block text-sm font-medium text-gray-700">
              次要关键词
            </label>
            <textarea
              id="candidate-secondary-keywords"
              value={form.secondary_keywords}
              onChange={(event) => setForm({ ...form, secondary_keywords: event.target.value })}
              className="mt-1 min-h-16 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label htmlFor="candidate-priority" className="block text-sm font-medium text-gray-700">
                优先级
              </label>
              <input
                id="candidate-priority"
                type="number"
                min={1}
                max={15}
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: Number(event.target.value) || 6 })}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="candidate-min-secondary-hits" className="block text-sm font-medium text-gray-700">
                最低次要命中
              </label>
              <input
                id="candidate-min-secondary-hits"
                type="number"
                min={0}
                max={10}
                value={form.min_secondary_hits}
                onChange={(event) => setForm({ ...form, min_secondary_hits: Number(event.target.value) || 0 })}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <label className="flex items-end gap-2 pb-2 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                checked={form.include_in_prompt}
                onChange={(event) => setForm({ ...form, include_in_prompt: event.target.checked })}
                className="h-4 w-4 accent-blue-600"
              />
              写入 Prompt
            </label>
          </div>
          <div>
            <label htmlFor="candidate-reviewer-note" className="block text-sm font-medium text-gray-700">
              审核备注
            </label>
            <input
              id="candidate-reviewer-note"
              value={form.reviewer_note}
              onChange={(event) => setForm({ ...form, reviewer_note: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          {error && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              审批通过
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items?: string[] }) {
  const values = items?.filter(Boolean) ?? [];
  return (
    <div className="rounded-lg border bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
      {values.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {values.map((item) => (
            <span key={item} className="rounded-md border bg-gray-50 px-2 py-1 text-xs text-gray-700">
              {item}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-gray-400">暂无绑定</p>
      )}
    </div>
  );
}

function InlinePillBlock({ title, items }: { title: string; items?: string[] }) {
  const values = items?.filter(Boolean) ?? [];
  return (
    <div>
      <p className="text-xs font-medium text-gray-500">{title}</p>
      {values.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {values.map((item) => (
            <span key={item} className="rounded-md border bg-white px-2 py-1 text-xs text-gray-700">
              {item}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-xs text-gray-400">暂无</p>
      )}
    </div>
  );
}

const addClassificationCriteria = [
  '连续出现低置信度或未识别输入，且不是表达别名或关键词缺失造成。',
  '现有 project_type 无法承载该空间对象，归并后会污染问卷、ontology 或知识召回。',
  '该类型需要独立的 ontology framework、activation pack、专业约束或交付逻辑。',
  '多个真实项目反复出现同一类空间需求，且有稳定样例和边界案例可验证。',
];

const addClassificationMechanism = [
  '先补 alias / keywords：只是叫法不同，不新增类型。',
  '再补 boundary_cases：只是容易和既有类型混淆，不新增类型。',
  '再补 subdomain：属于某个大类下的细分业态，例如 commercial_dining 下的 tea_drink_store。',
  '最后才新增 project_type：必须同步 meta、master index、profile、ontology 映射，并跑 registry 校验和回归测试。',
];

export default function SpaceClassificationAdminPage() {
  const [input, setInput] = useState('我想在购物中心开一家新茶饮店，主打外带和高峰取餐效率。');
  const [health, setHealth] = useState<RegistryHealth | null>(null);
  const [subdomainHealth, setSubdomainHealth] = useState<SubdomainHealth | null>(null);
  const [report, setReport] = useState<DiagnosticReport | null>(null);
  const [types, setTypes] = useState<SpaceClassificationType[]>([]);
  const [subdomains, setSubdomains] = useState<SubdomainRecord[]>([]);
  const [candidates, setCandidates] = useState<TypeCandidate[]>([]);
  const [candidateStats, setCandidateStats] = useState<CandidateStatistics>({});
  const [selectedType, setSelectedType] = useState<SpaceClassificationType | null>(null);
  const [approveTarget, setApproveTarget] = useState<TypeCandidate | null>(null);
  const [editForm, setEditForm] = useState({
    display_name: '',
    name_en: '',
    description: '',
    status: '',
    review_status: '',
    owner: '',
    ontology_framework_id: '',
  });
  const [addCandidateForm, setAddCandidateForm] = useState({
    type_id_suggestion: '',
    name_zh: '',
    name_en: '',
    description: '',
    suggested_keywords: '',
    sample_inputs: '',
  });
  const [showAddCandidate, setShowAddCandidate] = useState(false);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingTypes, setLoadingTypes] = useState(false);
  const [loadingSubdomains, setLoadingSubdomains] = useState(false);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [diagnosing, setDiagnosing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [addingCandidate, setAddingCandidate] = useState(false);
  const [error, setError] = useState('');

  const loadHealth = async () => {
    try {
      setLoadingHealth(true);
      setError('');
      const [registryRes, subdomainRes] = await Promise.all([
        axios.get(adminApi('/api/admin/space-classification/registry-health'), {
          headers: getAuthHeaders(),
        }),
        axios.get(adminApi('/api/admin/space-classification/subdomain-health'), {
          headers: getAuthHeaders(),
        }),
      ]);
      setHealth(registryRes.data);
      setSubdomainHealth(subdomainRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载 registry 健康失败');
    } finally {
      setLoadingHealth(false);
    }
  };

  const loadTypes = async () => {
    try {
      setLoadingTypes(true);
      setError('');
      const res = await axios.get(adminApi('/api/admin/space-classification/types'), {
        headers: getAuthHeaders(),
      });
      const items = res.data?.items ?? [];
      setTypes(items);
      if (!selectedType && items.length > 0) {
        selectType(items[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载空间分类列表失败');
    } finally {
      setLoadingTypes(false);
    }
  };

  const loadSubdomains = async () => {
    try {
      setLoadingSubdomains(true);
      setError('');
      const res = await axios.get(adminApi('/api/admin/space-classification/subdomains'), {
        headers: getAuthHeaders(),
      });
      setSubdomains(res.data?.items ?? []);
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载子域列表失败');
    } finally {
      setLoadingSubdomains(false);
    }
  };

  const loadCandidates = async () => {
    try {
      setLoadingCandidates(true);
      setError('');
      const res = await axios.get(adminApi('/api/admin/project-types/candidates?status=pending&limit=100'), {
        headers: getAuthHeaders(),
      });
      setCandidates(res.data?.items ?? []);
      setCandidateStats(res.data?.statistics ?? {});
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载空间分类候选失败');
    } finally {
      setLoadingCandidates(false);
    }
  };

  useEffect(() => {
    loadHealth();
    loadTypes();
    loadSubdomains();
    loadCandidates();
    // Initial admin data load only; handlers refresh their own data explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectType = (item: SpaceClassificationType) => {
    setSelectedType(item);
    setEditForm({
      display_name: item.display_name || '',
      name_en: item.name_en || '',
      description: item.description || '',
      status: item.status || '',
      review_status: item.review_status || '',
      owner: item.owner || '',
      ontology_framework_id: item.ontology_framework_id || '',
    });
  };

  const saveSelectedType = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedType) return;
    try {
      setSaving(true);
      setError('');
      const res = await axios.patch(
        adminApi(`/api/admin/space-classification/types/${selectedType.type_id}`),
        editForm,
        { headers: getAuthHeaders() }
      );
      const updated = res.data;
      setSelectedType(updated);
      setTypes((items) => items.map((item) => (item.type_id === updated.type_id ? updated : item)));
      selectType(updated);
    } catch (err: any) {
      setError(err.response?.data?.detail || '保存空间分类失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDiagnose = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim()) return;
    try {
      setDiagnosing(true);
      setError('');
      const res = await axios.post(
        adminApi('/api/admin/space-classification/diagnose'),
        { user_input: input.trim() },
        { headers: getAuthHeaders() }
      );
      setReport(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '识别失败');
    } finally {
      setDiagnosing(false);
    }
  };

  const rejectCandidate = async (candidate: TypeCandidate) => {
    if (!window.confirm(`确认拒绝候选「${candidate.type_id_suggestion}」？`)) return;
    try {
      setError('');
      await axios.post(
        adminApi(`/api/admin/project-types/candidates/${candidate.id}/reject`),
        { reason: '管理员拒绝' },
        { headers: getAuthHeaders() }
      );
      await loadCandidates();
    } catch (err: any) {
      setError(err.response?.data?.detail || '拒绝候选失败');
    }
  };

  const addCandidate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      setAddingCandidate(true);
      setError('');
      await axios.post(
        adminApi('/api/admin/project-types/candidates'),
        {
          type_id_suggestion: addCandidateForm.type_id_suggestion.trim(),
          name_zh: addCandidateForm.name_zh.trim(),
          name_en: addCandidateForm.name_en.trim(),
          description: addCandidateForm.description.trim(),
          suggested_keywords: addCandidateForm.suggested_keywords
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          sample_inputs: addCandidateForm.sample_inputs
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
        },
        { headers: getAuthHeaders() }
      );
      setShowAddCandidate(false);
      setAddCandidateForm({
        type_id_suggestion: '',
        name_zh: '',
        name_en: '',
        description: '',
        suggested_keywords: '',
        sample_inputs: '',
      });
      await loadCandidates();
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建候选失败');
    } finally {
      setAddingCandidate(false);
    }
  };

  const issueEntries = Object.entries(health?.issues ?? {}).filter(([, items]) => items.length > 0);
  const subdomainIssueEntries = Object.entries(subdomainHealth?.issues ?? {}).filter(([, items]) => items.length > 0);
  const pendingCandidateCount = candidateStats.pending?.count ?? candidates.length;
  const selectedProfile = selectedType?.type_operating_profile;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <div className="border-b bg-white px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold">空间分类</h1>
            <p className="mt-1 text-sm text-gray-500">
              查看和编辑空间分类治理字段，并检查 ontology、activation pack 和知识包覆盖。
            </p>
          </div>
          <button
            onClick={loadHealth}
            disabled={loadingHealth}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-60"
          >
            {loadingHealth ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            刷新健康度
          </button>
        </div>
      </div>

      <div className="space-y-6 p-6">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,0.7fr)]">
          <div className="rounded-lg border bg-white">
            <div className="flex items-center justify-between border-b px-5 py-4">
              <div>
                <h2 className="text-lg font-semibold">空间分类列表</h2>
                <p className="text-sm text-gray-500">
                  共 {types.length} 个类型，可编辑治理字段和 ontology framework 映射。
                </p>
              </div>
              {loadingTypes && <Loader2 className="h-5 w-5 animate-spin text-gray-400" />}
            </div>
            <div className="max-h-[480px] overflow-y-auto">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-3">类型</th>
                    <th className="px-4 py-3">父类</th>
                    <th className="px-4 py-3">Framework</th>
                    <th className="px-4 py-3">Profile</th>
                    <th className="px-4 py-3">状态</th>
                    <th className="px-4 py-3">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {types.map((item) => (
                    <tr
                      key={item.type_id}
                      className={selectedType?.type_id === item.type_id ? 'bg-blue-50' : 'hover:bg-gray-50'}
                    >
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{item.display_name}</div>
                        <div className="font-mono text-xs text-gray-500">{item.type_id}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{item.parent_type || '-'}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">
                        {item.ontology_framework_id || '-'}
                      </td>
                      <td className="px-4 py-3">
                        {item.has_type_operating_profile ? (
                          <div>
                            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                              Profile
                            </span>
                            <div className="mt-1 font-mono text-xs text-gray-500">{item.profile_id || '-'}</div>
                          </div>
                        ) : (
                          <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                            缺 profile
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${pillClass(item.review_status)}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          aria-label={`编辑 ${item.type_id}`}
                          onClick={() => selectType(item)}
                          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100"
                        >
                          编辑
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-lg border bg-white">
            <div className="border-b px-5 py-4">
              <h2 className="text-lg font-semibold">编辑空间分类</h2>
              <p className="text-sm text-gray-500">
                {selectedType ? selectedType.type_id : '请选择左侧空间分类'}
              </p>
            </div>
            {selectedType ? (
              <form onSubmit={saveSelectedType} className="space-y-4 p-5">
                <div>
                  <label htmlFor="type-display-name" className="block text-sm font-medium text-gray-700">
                    显示名称
                  </label>
                  <input
                    id="type-display-name"
                    value={editForm.display_name}
                    onChange={(event) => setEditForm({ ...editForm, display_name: event.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="type-name-en" className="block text-sm font-medium text-gray-700">
                    英文名
                  </label>
                  <input
                    id="type-name-en"
                    value={editForm.name_en}
                    onChange={(event) => setEditForm({ ...editForm, name_en: event.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="type-description" className="block text-sm font-medium text-gray-700">
                    说明
                  </label>
                  <textarea
                    id="type-description"
                    value={editForm.description}
                    onChange={(event) => setEditForm({ ...editForm, description: event.target.value })}
                    className="mt-1 min-h-24 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label htmlFor="type-status" className="block text-sm font-medium text-gray-700">
                      状态
                    </label>
                    <input
                      id="type-status"
                      value={editForm.status}
                      onChange={(event) => setEditForm({ ...editForm, status: event.target.value })}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor="type-review-status" className="block text-sm font-medium text-gray-700">
                      审核状态
                    </label>
                    <input
                      id="type-review-status"
                      value={editForm.review_status}
                      onChange={(event) => setEditForm({ ...editForm, review_status: event.target.value })}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="type-owner" className="block text-sm font-medium text-gray-700">
                    Owner
                  </label>
                  <input
                    id="type-owner"
                    value={editForm.owner}
                    onChange={(event) => setEditForm({ ...editForm, owner: event.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="type-framework" className="block text-sm font-medium text-gray-700">
                    Ontology Framework
                  </label>
                  <input
                    id="type-framework"
                    value={editForm.ontology_framework_id}
                    onChange={(event) => setEditForm({ ...editForm, ontology_framework_id: event.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm"
                  />
                </div>
                <div className="rounded-lg border bg-gray-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-gray-900">Type Operating Profile</h3>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-xs ${
                        selectedProfile?.issue_codes?.length
                          ? 'border-amber-200 bg-amber-50 text-amber-700'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      }`}
                    >
                      {selectedProfile?.issue_codes?.length ? '需复核' : '已对齐'}
                    </span>
                  </div>
                  {selectedProfile ? (
                    <div className="mt-3 space-y-3 text-sm">
                      <div className="grid gap-2 md:grid-cols-2">
                        <div>
                          <p className="text-xs text-gray-500">Profile ID</p>
                          <p className="mt-1 break-all font-mono text-xs text-gray-800">
                            {selectedProfile.profile_id || '-'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">方法画像</p>
                          <p className="mt-1 break-all font-mono text-xs text-gray-800">
                            {selectedProfile.type_method_profile_id || '-'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Master Framework</p>
                          <p className="mt-1 break-all font-mono text-xs text-gray-800">
                            {selectedProfile.master_index_ontology_framework || '-'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">一致性</p>
                          <p className="mt-1 text-xs text-gray-800">
                            {selectedProfile.framework_matches_master_index ? 'framework 匹配' : 'framework 不一致'}
                          </p>
                        </div>
                      </div>
                      <InlinePillBlock title="运行维度" items={selectedProfile.required_dimensions} />
                      <InlinePillBlock title="知识包绑定" items={selectedProfile.knowledge_package_ids} />
                      <InlinePillBlock title="缺失知识包引用" items={selectedProfile.missing_knowledge_package_ids} />
                      <InlinePillBlock
                        title="下游画像"
                        items={Object.values(selectedProfile.downstream_profiles ?? {}).filter(Boolean) as string[]}
                      />
                      <InlinePillBlock title="运行问题" items={selectedProfile.issue_codes} />
                    </div>
                  ) : (
                    <p className="mt-3 text-sm text-gray-500">暂无 Type Operating Profile 运行画像。</p>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  保存空间分类
                </button>
              </form>
            ) : (
              <p className="p-5 text-sm text-gray-500">暂无可编辑项。</p>
            )}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border bg-white p-5">
            <h2 className="text-lg font-semibold">什么时候需要增加空间分类</h2>
            <div className="mt-4 space-y-3">
              {addClassificationCriteria.map((item, index) => (
                <div key={item} className="flex gap-3 text-sm text-gray-700">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-700">
                    {index + 1}
                  </span>
                  <p>{item}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border bg-white p-5">
            <h2 className="text-lg font-semibold">新增机制</h2>
            <div className="mt-4 space-y-3">
              {addClassificationMechanism.map((item, index) => (
                <div key={item} className="flex gap-3 text-sm text-gray-700">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-xs font-semibold text-emerald-700">
                    {index + 1}
                  </span>
                  <p>{item}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-lg border bg-white">
          <div className="flex flex-col gap-4 border-b px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Network className="h-5 w-5 text-blue-600" />
                <h2 className="text-lg font-semibold">子域 Subdomain</h2>
                {subdomainHealth && (
                  <span className={`rounded-full border px-2 py-0.5 text-xs ${pillClass(subdomainHealth.status)}`}>
                    {subdomainHealth.status}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-gray-500">
                子域是项目类型下的细分业态，用于绑定 activation pack、知识包和专属问卷策略。
              </p>
            </div>
            <button
              type="button"
              onClick={loadSubdomains}
              disabled={loadingSubdomains}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-60"
            >
              {loadingSubdomains ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              刷新子域
            </button>
          </div>

          <div className="grid gap-3 border-b bg-gray-50 px-5 py-4 md:grid-cols-4">
            <Metric label="子域数量" value={subdomainHealth?.summary?.subdomain_count ?? subdomains.length} />
            <Metric label="激活包已加载" value={subdomainHealth?.summary?.activation_pack_loaded_count} />
            <Metric label="阻断问题" value={subdomainHealth?.summary?.blocking_issue_count} />
            <Metric label="警告问题" value={subdomainHealth?.summary?.warning_issue_count} />
          </div>

          {subdomainIssueEntries.length > 0 && (
            <div className="border-b border-amber-200 bg-amber-50 px-5 py-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                子域绑定需要跟进
              </h3>
              <div className="mt-3 space-y-2">
                {subdomainIssueEntries.map(([key, items]) => (
                  <div key={key} className="text-sm text-amber-800">
                    <span className="font-mono text-xs">{key}</span>
                    <span className="ml-2 text-amber-700">{items.slice(0, 6).join(', ')}</span>
                    {items.length > 6 && <span className="ml-1">等 {items.length} 项</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="p-5">
            {loadingSubdomains ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-7 w-7 animate-spin text-gray-400" />
              </div>
            ) : subdomains.length === 0 ? (
              <div className="rounded-lg border border-dashed bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
                暂无子域配置。
              </div>
            ) : (
              <div className="grid gap-4 xl:grid-cols-2">
                {subdomains.map((item) => (
                  <div key={item.subdomain_id} className="rounded-lg border p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium text-gray-900">{item.name_cn}</span>
                          <span className="rounded-md bg-gray-100 px-2 py-1 font-mono text-xs text-gray-700">
                            {item.subdomain_id}
                          </span>
                          <span className={`rounded-full border px-2 py-0.5 text-xs ${pillClass(item.status)}`}>
                            {item.status || '-'}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-gray-500">
                          父类型：{item.parent_project_type_name || item.parent_project_type_id || '-'}
                          <span className="mx-2 text-gray-300">/</span>
                          Framework：<span className="font-mono text-xs">{item.ontology_framework_id || '-'}</span>
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${item.activation_pack_loaded ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}>
                          {item.activation_pack_loaded ? '已加载' : '未加载'}
                        </span>
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${item.routing_binding_matched ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
                          {item.routing_binding_matched ? 'routing 匹配' : 'routing 不匹配'}
                        </span>
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${item.has_runtime_detector_binding ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}>
                          {item.has_runtime_detector_binding ? 'detector 已绑定' : 'detector 未绑定'}
                        </span>
                      </div>
                    </div>

                    <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
                      <div className="rounded-lg bg-gray-50 p-3">
                        <dt className="text-xs text-gray-500">Activation Pack</dt>
                        <dd className="mt-1 font-mono text-xs text-gray-800">{item.activation_pack_id || '-'}</dd>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-3">
                        <dt className="text-xs text-gray-500">知识包</dt>
                        <dd className="mt-1 font-mono text-xs text-gray-800">
                          {(item.knowledge_package_ids || []).slice(0, 3).join(', ') || '-'}
                        </dd>
                      </div>
                    </dl>

                    <div className="mt-4">
                      <p className="text-xs font-semibold uppercase text-gray-500">识别关键词</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {(item.signal_keywords || []).slice(0, 8).map((keyword) => (
                          <span key={keyword} className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="rounded-lg border bg-white">
          <div className="flex flex-col gap-4 border-b px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-blue-600" />
                <h2 className="text-lg font-semibold">候选发现</h2>
              </div>
              <p className="mt-1 text-sm text-gray-500">
                后端会沉淀未识别或低置信输入产生的候选；这里负责人工复核后再进入空间分类体系。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={loadCandidates}
                disabled={loadingCandidates}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-60"
              >
                {loadingCandidates ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                刷新候选
              </button>
              <button
                type="button"
                onClick={() => setShowAddCandidate(true)}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                手动添加候选
              </button>
            </div>
          </div>

          <div className="grid gap-3 border-b bg-gray-50 px-5 py-4 md:grid-cols-3">
            <Metric label="待人工复核" value={pendingCandidateCount} />
            <Metric label="已批准候选" value={candidateStats.approved?.count} />
            <Metric label="已拒绝候选" value={candidateStats.rejected?.count} />
          </div>

          <div className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-semibold">人工复核</h3>
              <span className="text-sm text-gray-500">当前筛选：pending</span>
            </div>

            {loadingCandidates ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-7 w-7 animate-spin text-gray-400" />
              </div>
            ) : candidates.length === 0 ? (
              <div className="rounded-lg border border-dashed bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
                暂无待复核空间分类候选。
              </div>
            ) : (
              <div className="space-y-3">
                {candidates.map((candidate) => (
                  <div key={candidate.id} className="rounded-lg border p-4">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-md bg-gray-100 px-2 py-1 font-mono text-xs text-gray-700">
                            {candidate.type_id_suggestion}
                          </span>
                          <span className="font-medium text-gray-900">{candidate.name_zh}</span>
                          <span className={`rounded-full border px-2 py-0.5 text-xs ${confidenceClass(candidate.confidence_score)}`}>
                            {Math.round(candidate.confidence_score * 100)}% 置信
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                          <span>来源：{sourceLabel(candidate.source)}</span>
                          <span>出现：{candidate.occurrence_count} 次</span>
                          <span>创建：{new Date(candidate.created_at).toLocaleDateString('zh-CN')}</span>
                          {candidate.source_session_id && (
                            <span className="font-mono">会话：{candidate.source_session_id.slice(-8)}</span>
                          )}
                        </div>
                        {candidate.description && (
                          <p className="mt-2 text-sm text-gray-600">{candidate.description}</p>
                        )}
                        {candidate.suggested_keywords.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {candidate.suggested_keywords.map((keyword) => (
                              <span key={keyword} className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                                {keyword}
                              </span>
                            ))}
                          </div>
                        )}
                        {candidate.sample_inputs[0] && (
                          <p className="mt-2 truncate text-xs text-gray-400">样例：{candidate.sample_inputs[0]}</p>
                        )}
                      </div>
                      {candidate.review_status === 'pending' ? (
                        <div className="flex shrink-0 gap-2">
                          <button
                            type="button"
                            aria-label={`审批候选 ${candidate.type_id_suggestion}`}
                            onClick={() => setApproveTarget(candidate)}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                            审批
                          </button>
                          <button
                            type="button"
                            aria-label={`拒绝候选 ${candidate.type_id_suggestion}`}
                            onClick={() => rejectCandidate(candidate)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                          >
                            <XCircle className="h-4 w-4" />
                            拒绝
                          </button>
                        </div>
                      ) : (
                        <span className={`rounded-full border px-3 py-1 text-xs ${pillClass(candidate.review_status)}`}>
                          {candidate.review_status}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="rounded-lg border bg-white p-5">
          <form onSubmit={handleDiagnose} className="space-y-3">
            <label htmlFor="project-description" className="block text-sm font-semibold text-gray-800">
              项目描述
            </label>
            <textarea
              id="project-description"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              className="min-h-28 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              placeholder="输入一个项目描述，用于识别空间分类链路"
            />
            <button
              type="submit"
              disabled={diagnosing || !input.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {diagnosing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              识别空间分类
            </button>
          </form>
        </section>

        <section>
          <div className="mb-3 flex items-center gap-2">
            <Network className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-semibold">Registry 健康</h2>
            {health && (
              <span className={`rounded-full border px-2 py-0.5 text-xs ${pillClass(health.status)}`}>
                {health.status}
              </span>
            )}
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <Metric label="项目类型" value={health?.summary?.project_type_count} />
            <Metric label="Ontology 维度" value={health?.summary?.ontology_dimension_count} />
            <Metric label="阻断问题" value={health?.summary?.blocking_issue_count} />
            <Metric label="警告问题" value={health?.summary?.warning_issue_count} />
          </div>
          {issueEntries.length > 0 && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                需要跟进的 registry 缺口
              </h3>
              <div className="mt-3 space-y-2">
                {issueEntries.map(([key, items]) => (
                  <div key={key} className="text-sm text-amber-800">
                    <span className="font-mono text-xs">{key}</span>
                    <span className="ml-2 text-amber-700">{items.slice(0, 6).join(', ')}</span>
                    {items.length > 6 && <span className="ml-1">等 {items.length} 项</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {report && (
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              <h2 className="text-lg font-semibold">识别结果</h2>
              <span className={`rounded-full border px-2 py-0.5 text-xs ${pillClass(report.health.severity)}`}>
                {report.health.severity}
              </span>
            </div>

            {report.normalization_trace && (
              <div className="rounded-lg border bg-white p-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="text-sm font-semibold text-gray-800">关键词归一过程</h3>
                  <span className={`rounded-full border px-2 py-0.5 text-xs ${pillClass(report.normalization_trace.changed ? 'warning' : 'ok')}`}>
                    {report.normalization_trace.changed ? '已归一' : '未变化'}
                  </span>
                </div>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  <dl className="rounded-lg border bg-gray-50 p-3 text-sm">
                    <dt className="text-xs text-gray-500">原始输入</dt>
                    <dd className="mt-1 whitespace-pre-wrap break-words text-gray-800">
                      {report.normalization_trace.original_text || '-'}
                    </dd>
                  </dl>
                  <dl className="rounded-lg border bg-gray-50 p-3 text-sm">
                    <dt className="text-xs text-gray-500">归一后输入</dt>
                    <dd className="mt-1 whitespace-pre-wrap break-words text-gray-800">
                      {report.normalization_trace.normalized_text || '-'}
                    </dd>
                  </dl>
                </div>
                {(report.normalization_trace.replacements || []).length > 0 && (
                  <div className="mt-4 overflow-hidden rounded-lg border">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                        <tr>
                          <th className="px-3 py-2">原词</th>
                          <th className="px-3 py-2">标准词</th>
                          <th className="px-3 py-2">来源</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y bg-white">
                        {(report.normalization_trace.replacements || []).map((item, index) => (
                          <tr key={`${item.alias}-${item.canonical}-${index}`}>
                            <td className="px-3 py-2 font-mono text-xs text-gray-800">{item.alias}</td>
                            <td className="px-3 py-2 font-mono text-xs text-gray-800">{item.canonical}</td>
                            <td className="px-3 py-2 font-mono text-xs text-gray-500">{item.source || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-lg border bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-800">分类结果</h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">类型</dt>
                    <dd className="font-medium">{report.classification.project_type_name || report.classification.project_type}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">置信度</dt>
                    <dd>{Math.round((report.classification.confidence ?? 0) * 100)}%</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">状态</dt>
                    <dd>{report.classification.status}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">主桶</dt>
                    <dd>{report.classification.primary_bucket}</dd>
                  </div>
                </dl>
              </div>

              <div className="rounded-lg border bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-800">绑定链</h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Framework</dt>
                    <dd className="font-mono text-xs">{report.binding_summary.ontology_framework_id || '-'}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Subdomain</dt>
                    <dd className="font-mono text-xs">{report.binding_summary.subdomain_id || '-'}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Activation Pack</dt>
                    <dd className="font-mono text-xs">{report.binding_summary.activation_pack_id || '-'}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Secondary Packs</dt>
                    <dd className="max-w-[220px] truncate font-mono text-xs">
                      {(report.binding_summary.secondary_activation_pack_ids || []).join(', ') || '-'}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Project Scale</dt>
                    <dd className="font-mono text-xs">{report.binding_summary.project_scale || '-'}</dd>
                  </div>
                </dl>
              </div>

              <div className="rounded-lg border bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-800">覆盖状态</h3>
                <p className="mt-3 text-sm text-gray-600">
                  阻断 {report.health.blocking_count} 项，警告 {report.health.warning_count} 项。
                </p>
                <p className="mt-2 text-sm text-gray-600">
                  激活包文件：{report.activation_pack_preview.loaded ? '已加载' : '未加载'}
                </p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <ListBlock title="Ontology Dimensions" items={report.binding_summary.ontology_dimension_ids} />
              <ListBlock title="Knowledge Packages" items={report.binding_summary.knowledge_package_ids} />
              <ListBlock title="Spatial Layers" items={report.binding_summary.spatial_layer_ids} />
            </div>

            {(report.activation_pack_coordination || report.context_packet?.activation_pack_coordination) && (
              <div className="rounded-lg border bg-white p-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800">Activation Pack Coordination</h3>
                    <p className="mt-1 text-xs text-gray-500">
                      复合空间下主分类不被子业态覆盖，协同包只以增量方式补充知识、专业和追问槽。
                    </p>
                  </div>
                  <span className="rounded-md border bg-gray-50 px-2 py-1 font-mono text-xs text-gray-600">
                    {(report.activation_pack_coordination || report.context_packet?.activation_pack_coordination)?.schema_version}
                  </span>
                </div>

                <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                  <div className="rounded-lg bg-gray-50 p-3">
                    <dt className="text-xs text-gray-500">Mode</dt>
                    <dd className="mt-1 font-mono text-xs text-gray-800">
                      {(report.activation_pack_coordination || report.context_packet?.activation_pack_coordination)?.mode || '-'}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3">
                    <dt className="text-xs text-gray-500">Loaded Packs</dt>
                    <dd className="mt-1 font-mono text-xs text-gray-800">
                      {((report.activation_pack_coordination || report.context_packet?.activation_pack_coordination)?.loaded_pack_ids || []).join(', ') || '-'}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3">
                    <dt className="text-xs text-gray-500">Merge Policy</dt>
                    <dd className="mt-1 font-mono text-xs text-gray-800">
                      {(report.activation_pack_coordination || report.context_packet?.activation_pack_coordination)?.merge_policy || '-'}
                    </dd>
                  </div>
                </dl>

                {((report.activation_pack_coordination || report.context_packet?.activation_pack_coordination)?.secondary_packs || []).length > 0 && (
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {((report.activation_pack_coordination || report.context_packet?.activation_pack_coordination)?.secondary_packs || []).map((item) => (
                      <div key={`${item.pack_id}-${item.subdomain_id}`} className="rounded-lg border bg-gray-50 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-mono text-xs font-semibold text-gray-800">{item.pack_id || '-'}</span>
                          <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                            {Math.round((item.confidence ?? 0) * 100)}%
                          </span>
                        </div>
                        <dl className="mt-3 space-y-1 text-xs text-gray-600">
                          <div className="flex justify-between gap-3">
                            <dt>Subdomain</dt>
                            <dd className="font-mono">{item.subdomain_id || '-'}</dd>
                          </div>
                          <div className="flex justify-between gap-3">
                            <dt>Role</dt>
                            <dd className="font-mono">{item.role || '-'}</dd>
                          </div>
                        </dl>
                        {(item.matched_keywords || []).length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {(item.matched_keywords || []).map((keyword) => (
                              <span key={keyword} className="rounded bg-white px-2 py-0.5 text-xs text-gray-700">
                                {keyword}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {(report.subdomain_signals || []).length > 0 && (
              <div className="rounded-lg border bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-800">Subdomain Signals</h3>
                <p className="mt-1 text-xs text-gray-500">
                  detector 输出的子域候选信号；最终冻结结果仍以 classification_output.subdomain_id 为准。
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {(report.subdomain_signals || []).map((signal) => (
                    <div
                      key={`${signal.suggested_subdomain_id}-${signal.activation_pack_id}`}
                      className="rounded-lg border bg-gray-50 p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-mono text-xs font-semibold text-gray-800">
                          {signal.suggested_subdomain_id || '-'}
                        </span>
                        <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                          {Math.round((signal.confidence ?? 0) * 100)}%
                        </span>
                      </div>
                      <p className="mt-2 font-mono text-xs text-gray-500">
                        {signal.activation_pack_id || '-'}
                      </p>
                      {(signal.matched_keywords || []).length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {(signal.matched_keywords || []).map((keyword) => (
                            <span key={keyword} className="rounded bg-white px-2 py-0.5 text-xs text-gray-700">
                              {keyword}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(report.founding_type_candidates || []).length > 0 && (
              <div className="rounded-lg border bg-white p-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800">Founding Type Candidates</h3>
                    <p className="mt-1 text-xs text-gray-500">
                      detector 输出的项目成立方式候选；最终冻结结果仍以 classification_output.founding_type 为准。
                    </p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {(report.founding_type_candidates || []).map((candidate) => {
                    const keywords = [
                      ...(candidate.matched_keywords?.primary || []),
                      ...(candidate.matched_keywords?.secondary || []),
                    ];
                    return (
                      <div
                        key={`${candidate.founding_type_id}-${candidate.confidence}`}
                        className="rounded-lg border bg-gray-50 p-3"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-mono text-xs text-gray-800">
                            {candidate.founding_type_id || '-'}
                          </span>
                          <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                            {Math.round((candidate.confidence || 0) * 100)}%
                          </span>
                        </div>
                        {keywords.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {keywords.map((keyword) => (
                              <span key={keyword} className="rounded bg-white px-2 py-0.5 text-xs text-gray-700">
                                {keyword}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {report.classification_output && (
              <div className="rounded-lg border bg-white p-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800">Classification Output</h3>
                    <p className="mt-1 text-xs text-gray-500">
                      v1.8 正式分类对象：供 activation pack、ontology、知识召回和任务书编排统一消费。
                    </p>
                  </div>
                  <span className="rounded-md border bg-gray-50 px-2 py-1 font-mono text-xs text-gray-600">
                    {report.classification_output.schema_version}
                  </span>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  <dl className="rounded-lg border bg-gray-50 p-3 text-sm">
                    <dt className="text-xs text-gray-500">Project Type</dt>
                    <dd className="mt-1 font-mono text-xs text-gray-800">
                      {report.classification_output.project_type_id || '-'}
                    </dd>
                  </dl>
                  <dl className="rounded-lg border bg-gray-50 p-3 text-sm">
                    <dt className="text-xs text-gray-500">Founding Type</dt>
                    <dd className="mt-1 font-mono text-xs text-gray-800">
                      {report.classification_output.founding_type || '-'}
                    </dd>
                  </dl>
                  <dl className="rounded-lg border bg-gray-50 p-3 text-sm">
                    <dt className="text-xs text-gray-500">Project Scale</dt>
                    <dd className="mt-1 font-mono text-xs text-gray-800">
                      {report.classification_output.project_scale || '-'}
                    </dd>
                  </dl>
                  <dl className="rounded-lg border bg-gray-50 p-3 text-sm">
                    <dt className="text-xs text-gray-500">Lead Discipline</dt>
                    <dd className="mt-1 font-mono text-xs text-gray-800">
                      {report.classification_output.lead_discipline || '-'}
                    </dd>
                  </dl>
                </div>
                <div className="mt-3 grid gap-3 lg:grid-cols-3">
                  <ListBlock title="Disciplines" items={report.classification_output.discipline_scope} />
                  <ListBlock title="Hard Constraints" items={report.classification_output.hard_constraint_discipline_ids} />
                  <ListBlock title="Project Conditions" items={report.classification_output.project_conditions} />
                </div>
              </div>
            )}

            {report.context_packet && (
              <div className="rounded-lg border bg-white p-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800">Context Packet</h3>
                    <p className="mt-1 text-xs text-gray-500">
                      v3.3 上下文包：把空间分类、语境向量、输出模式、学科切换和缺口分流收束为同一运行对象。
                    </p>
                  </div>
                  <span className="rounded-md border bg-gray-50 px-2 py-1 font-mono text-xs text-gray-600">
                    {report.context_packet.schema_version}
                  </span>
                </div>

                <div className="mt-4 grid gap-4 lg:grid-cols-4">
                  <div className="rounded-lg border bg-gray-50 p-3">
                    <h4 className="text-xs font-semibold uppercase text-gray-500">Classification</h4>
                    <dl className="mt-3 space-y-2 text-sm">
                      <div>
                        <dt className="text-xs text-gray-500">Project Type</dt>
                        <dd className="font-mono text-xs text-gray-800">
                          {report.context_packet.classification?.project_type_id || '-'}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-gray-500">Subdomain</dt>
                        <dd className="font-mono text-xs text-gray-800">
                          {report.context_packet.classification?.subdomain?.primary_subdomain_id || '-'}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-gray-500">Founding Type</dt>
                        <dd className="font-mono text-xs text-gray-800">
                          {report.context_packet.classification?.founding_type_id || '-'}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  <div className="rounded-lg border bg-gray-50 p-3">
                    <h4 className="text-xs font-semibold uppercase text-gray-500">Context Vector</h4>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {[
                        report.context_packet.context_vector?.primary_space_type,
                        report.context_packet.context_vector?.site_context,
                        report.context_packet.context_vector?.service_mode,
                        report.context_packet.context_vector?.investment_boundary,
                      ]
                        .filter(Boolean)
                        .map((item) => (
                          <span key={item} className="rounded border bg-white px-2 py-0.5 font-mono text-xs text-gray-700">
                            {item}
                          </span>
                        ))}
                    </div>
                  </div>

                  <div className="rounded-lg border bg-gray-50 p-3">
                    <h4 className="text-xs font-semibold uppercase text-gray-500">Output Mode</h4>
                    <dl className="mt-3 space-y-2 text-sm">
                      <div>
                        <dt className="text-xs text-gray-500">Primary</dt>
                        <dd className="font-mono text-xs text-gray-800">
                          {report.context_packet.output_mode?.primary_output_mode || '-'}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-gray-500">Container</dt>
                        <dd className="font-mono text-xs text-gray-800">
                          {report.context_packet.output_mode?.user_visible_container || '-'}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  <div className="rounded-lg border bg-gray-50 p-3">
                    <h4 className="text-xs font-semibold uppercase text-gray-500">Discipline Switch</h4>
                    <dl className="mt-3 space-y-2 text-sm">
                      <div>
                        <dt className="text-xs text-gray-500">Extent</dt>
                        <dd className="font-mono text-xs text-gray-800">
                          {report.context_packet.discipline_switch?.spatial_extent_level || '-'}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-gray-500">Coverage</dt>
                        <dd className="font-mono text-xs text-gray-800">
                          {report.context_packet.discipline_switch?.current_coverage || '-'}
                        </dd>
                      </div>
                    </dl>
                  </div>
                </div>

                <div className="mt-4 rounded-lg border bg-gray-50 p-3">
                  <h4 className="text-xs font-semibold uppercase text-gray-500">Packet Governance</h4>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <div>
                      <dt className="text-xs text-gray-500">Ontology Framework</dt>
                      <dd className="mt-1 font-mono text-xs text-gray-800">
                        {report.context_packet.ontology_binding?.ontology_framework_id || '-'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-gray-500">Loaded Activation Packs</dt>
                      <dd className="mt-1 flex flex-wrap gap-1.5">
                        {(
                          report.context_packet.activation_pack_coordination?.loaded_pack_ids ||
                          [
                            report.context_packet.ontology_binding?.activation_pack_id,
                            ...(report.context_packet.ontology_binding?.secondary_activation_pack_ids || []),
                          ].filter(Boolean)
                        ).length > 0 ? (
                          (
                            report.context_packet.activation_pack_coordination?.loaded_pack_ids ||
                            [
                              report.context_packet.ontology_binding?.activation_pack_id,
                              ...(report.context_packet.ontology_binding?.secondary_activation_pack_ids || []),
                            ].filter(Boolean)
                          ).map((packId) => (
                            <span key={packId} className="rounded border bg-white px-2 py-0.5 font-mono text-xs text-gray-700">
                              {packId}
                            </span>
                          ))
                        ) : (
                          <span className="font-mono text-xs text-gray-400">-</span>
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-gray-500">Knowledge Packages</dt>
                      <dd className="mt-1 flex flex-wrap gap-1.5">
                        {(report.context_packet.knowledge_binding?.knowledge_package_ids || []).length > 0 ? (
                          report.context_packet.knowledge_binding?.knowledge_package_ids?.map((packageId) => (
                            <span key={packageId} className="rounded border bg-white px-2 py-0.5 font-mono text-xs text-gray-700">
                              {packageId}
                            </span>
                          ))
                        ) : (
                          <span className="font-mono text-xs text-gray-400">-</span>
                        )}
                      </dd>
                    </div>
                  </div>
                </div>

                {report.capability_plan && (
                  <div className="mt-4 rounded-lg border bg-gray-50 p-3">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h4 className="text-xs font-semibold uppercase text-gray-500">Capability Plan</h4>
                        <p className="mt-1 text-xs text-gray-500">
                          本轮运行能力：理解、检索、推理、转译、生成和沉淀治理的守门状态。
                        </p>
                      </div>
                      <span className="rounded-md border bg-white px-2 py-1 font-mono text-xs text-gray-600">
                        {report.capability_plan.schema_version || '-'}
                      </span>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-4">
                      <dl>
                        <dt className="text-xs text-gray-500">状态</dt>
                        <dd className="mt-1">
                          <span className={`rounded border px-2 py-0.5 text-xs ${pillClass(report.capability_plan.status)}`}>
                            {report.capability_plan.status || '-'}
                          </span>
                        </dd>
                      </dl>
                      <dl>
                        <dt className="text-xs text-gray-500">成熟度封顶</dt>
                        <dd className="mt-1 font-mono text-xs text-gray-800">
                          {report.capability_plan.maturity_ceiling || '-'}
                        </dd>
                      </dl>
                      <dl>
                        <dt className="text-xs text-gray-500">输出模式</dt>
                        <dd className="mt-1 font-mono text-xs text-gray-800">
                          {report.capability_plan.output_mode || '-'}
                        </dd>
                      </dl>
                      <dl>
                        <dt className="text-xs text-gray-500">学科覆盖</dt>
                        <dd className="mt-1 font-mono text-xs text-gray-800">
                          {report.capability_plan.discipline_coverage || '-'}
                        </dd>
                      </dl>
                    </div>
                    {report.capability_plan.registry && (
                      <div className="mt-3 rounded-md border bg-white px-3 py-2">
                        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700">Capability Registry</h5>
                            <p className="mt-1 break-all font-mono text-xs text-gray-500">
                              {report.capability_plan.registry.path || '-'}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            <span className="rounded border bg-gray-50 px-2 py-0.5 font-mono text-xs text-gray-700">
                              {report.capability_plan.registry.schema_version || '-'}
                            </span>
                            <span className={`rounded border px-2 py-0.5 text-xs ${pillClass(report.capability_plan.registry.status)}`}>
                              {report.capability_plan.registry.status || '-'}
                            </span>
                          </div>
                        </div>
                        {(report.capability_plan.registry.issues || []).length > 0 && (
                          <div className="mt-2 space-y-1">
                            {report.capability_plan.registry.issues?.map((issue) => (
                              <div key={`${issue.code}-${issue.message}`} className="rounded border bg-amber-50 px-2 py-1 text-xs text-amber-800">
                                <span className="font-mono">{issue.code || 'registry_issue'}</span>
                                {issue.message && <span className="ml-2">{issue.message}</span>}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    <div className="mt-3 grid gap-2 lg:grid-cols-3">
                      {(report.capability_plan.capability_nodes || []).map((node) => (
                        <div key={node.capability_group || node.name} className="rounded-md border bg-white px-3 py-2 text-sm">
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <span className="font-mono text-xs font-semibold text-gray-800">
                                {node.capability_group || '-'}
                              </span>
                              {node.name && <span className="ml-2 text-xs text-gray-500">{node.name}</span>}
                            </div>
                            <span className={`rounded border px-2 py-0.5 text-xs ${pillClass(node.status)}`}>
                              {node.status || '-'}
                            </span>
                          </div>
                          {node.primary_principle && (
                            <p className="mt-2 text-xs text-gray-700">{node.primary_principle}</p>
                          )}
                          {node.maturity_ceiling_rule && (
                            <p className="mt-1 font-mono text-xs text-amber-700">{node.maturity_ceiling_rule}</p>
                          )}
                          {node.evidence_requirement && (
                            <p className="mt-1 font-mono text-xs text-blue-700">{node.evidence_requirement}</p>
                          )}
                          {(node.blocking_missing_slots || []).length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {node.blocking_missing_slots?.map((slot) => (
                                <span key={slot} className="rounded border bg-amber-50 px-2 py-0.5 font-mono text-xs text-amber-700">
                                  {slot}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(report.context_packet.missing_slots?.length ?? 0) > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold uppercase text-gray-500">Missing Slots</h4>
                    <div className="mt-2 space-y-2">
                      {report.context_packet.missing_slots?.slice(0, 4).map((slot) => (
                        <div key={`${slot.name}-${slot.action}`} className="rounded-md border bg-gray-50 px-3 py-2 text-sm">
                          <span className={`mr-2 rounded border px-2 py-0.5 text-xs ${pillClass(slot.severity)}`}>
                            {slot.severity || 'medium'}
                          </span>
                          <span className={`mr-2 rounded border px-2 py-0.5 text-xs ${
                            slot.active_for_current_round === false
                              ? 'border-gray-200 bg-gray-100 text-gray-600'
                              : 'border-blue-200 bg-blue-50 text-blue-700'
                          }`}>
                            {slot.active_for_current_round === false ? '后置' : '本轮追问'}
                          </span>
                          <span className="font-mono text-xs text-gray-700">{slot.name}</span>
                          {slot.action && <span className="ml-2 font-mono text-xs text-gray-400">{slot.action}</span>}
                          {slot.deferred_by && <span className="ml-2 font-mono text-xs text-amber-600">{slot.deferred_by}</span>}
                          {slot.user_visible_note && <p className="mt-1 text-gray-600">{slot.user_visible_note}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {report.coverage_gaps.length > 0 && (
              <div className="rounded-lg border bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-800">覆盖缺口</h3>
                <div className="mt-3 space-y-2">
                  {report.coverage_gaps.map((gap) => (
                    <div key={gap.code} className="rounded-md border bg-gray-50 px-3 py-2 text-sm">
                      <span className={`mr-2 rounded border px-2 py-0.5 text-xs ${pillClass(gap.severity)}`}>
                        {gap.severity}
                      </span>
                      <span className="font-mono text-xs text-gray-500">{gap.code}</span>
                      <p className="mt-1 text-gray-700">{gap.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </div>

      {approveTarget && (
        <ApproveCandidateModal
          candidate={approveTarget}
          onClose={() => setApproveTarget(null)}
          onDone={() => {
            setApproveTarget(null);
            loadCandidates();
            loadTypes();
            loadHealth();
          }}
        />
      )}

      {showAddCandidate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
            <div className="border-b px-5 py-4">
              <h3 className="text-lg font-semibold">手动添加空间分类候选</h3>
              <p className="mt-1 text-sm text-gray-500">用于补录自动发现遗漏但确实需要复核的新空间分类。</p>
            </div>
            <form onSubmit={addCandidate} className="space-y-4 p-5">
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label htmlFor="new-candidate-type-id" className="block text-sm font-medium text-gray-700">
                    建议英文 ID
                  </label>
                  <input
                    id="new-candidate-type-id"
                    value={addCandidateForm.type_id_suggestion}
                    onChange={(event) =>
                      setAddCandidateForm({ ...addCandidateForm, type_id_suggestion: event.target.value })
                    }
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm"
                    placeholder="elderly_day_care"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="new-candidate-name-zh" className="block text-sm font-medium text-gray-700">
                    中文名
                  </label>
                  <input
                    id="new-candidate-name-zh"
                    value={addCandidateForm.name_zh}
                    onChange={(event) => setAddCandidateForm({ ...addCandidateForm, name_zh: event.target.value })}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    placeholder="长者日间照护"
                    required
                  />
                </div>
              </div>
              <div>
                <label htmlFor="new-candidate-name-en" className="block text-sm font-medium text-gray-700">
                  英文检索词
                </label>
                <input
                  id="new-candidate-name-en"
                  value={addCandidateForm.name_en}
                  onChange={(event) => setAddCandidateForm({ ...addCandidateForm, name_en: event.target.value })}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label htmlFor="new-candidate-keywords" className="block text-sm font-medium text-gray-700">
                  建议关键词
                </label>
                <input
                  id="new-candidate-keywords"
                  value={addCandidateForm.suggested_keywords}
                  onChange={(event) =>
                    setAddCandidateForm({ ...addCandidateForm, suggested_keywords: event.target.value })
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="长者照护, 日间照料"
                />
              </div>
              <div>
                <label htmlFor="new-candidate-description" className="block text-sm font-medium text-gray-700">
                  说明
                </label>
                <textarea
                  id="new-candidate-description"
                  value={addCandidateForm.description}
                  onChange={(event) =>
                    setAddCandidateForm({ ...addCandidateForm, description: event.target.value })
                  }
                  className="mt-1 min-h-20 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label htmlFor="new-candidate-samples" className="block text-sm font-medium text-gray-700">
                  样例输入
                </label>
                <textarea
                  id="new-candidate-samples"
                  value={addCandidateForm.sample_inputs}
                  onChange={(event) =>
                    setAddCandidateForm({ ...addCandidateForm, sample_inputs: event.target.value })
                  }
                  className="mt-1 min-h-20 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="一行一个真实项目表达"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddCandidate(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={addingCandidate}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                >
                  {addingCandidate && <Loader2 className="h-4 w-4 animate-spin" />}
                  创建候选
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
