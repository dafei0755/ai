'use client';

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { ChevronRight, ChevronDown, Search, RefreshCw } from 'lucide-react';

interface Framework {
  id: string;
  name: string;
  categories: string[];
  total_dimensions: number;
}

interface Category {
  id: string;
  name: string;
  dimensions: Dimension[];
}

interface Dimension {
  name: string;
  description: string;
  ask_yourself: string;
  examples: string;
}

interface FrameworkDetail {
  id: string;
  name: string;
  categories: Category[];
}

interface OntologyDiagnosticFramework {
  framework_id: string;
  project_type_ids: string[];
  activation_pack_ids: string[];
  dimension_count?: number;
}

interface OntologyDiagnosticDimension {
  dimension_id: string;
  name_cn?: string;
  spatial_layer_ids: string[];
  activation_pack_ids: string[];
  approved_card_count: number;
}

interface OntologyDiagnostics {
  schema_version: string;
  status: string;
  summary: {
    framework_count: number;
    dimension_count: number;
    project_type_framework_mapping_count: number;
    spatial_layer_dimension_mapping_count: number;
    approved_card_dimension_count: number;
    blocking_issue_count: number;
    warning_issue_count: number;
  };
  frameworks: OntologyDiagnosticFramework[];
  dimensions: OntologyDiagnosticDimension[];
  issues: Record<string, string[]>;
}

export default function OntologyBrowserPage() {
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [selectedFramework, setSelectedFramework] = useState<FrameworkDetail | null>(null);
  const [selectedDimension, setSelectedDimension] = useState<Dimension | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string>('');
  const [diagnostics, setDiagnostics] = useState<OntologyDiagnostics | null>(null);

  const getAuthHeaders = useCallback(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('app_auth_token') : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  // 加载框架列表
  const fetchFrameworks = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      console.log('🔍 正在加载框架列表...');
      const res = await axios.get('/api/admin/ontology/frameworks', { headers: getAuthHeaders() });
      console.log('✅ 框架列表加载成功:', res.data);
      setFrameworks(res.data);
    } catch (error: any) {
      console.error('❌ 加载框架列表失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      setError(`加载框架列表失败: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  const fetchDiagnostics = useCallback(async () => {
    try {
      const res = await axios.get('/api/admin/ontology/diagnostics', { headers: getAuthHeaders() });
      setDiagnostics(res.data);
    } catch (error: any) {
      console.error('❌ 加载本体论诊断失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      setError(`加载本体论诊断失败: ${errorMsg}`);
    }
  }, [getAuthHeaders]);

  useEffect(() => {
    fetchFrameworks();
    fetchDiagnostics();
  }, [fetchFrameworks, fetchDiagnostics]);

  // 加载框架详情
  const loadFrameworkDetail = async (frameworkId: string) => {
    try {
      setLoadingDetail(true);
      setError('');
      console.log(`🔍 正在加载框架详情: ${frameworkId}`);
      const res = await axios.get(`/api/admin/ontology/framework/${frameworkId}`, { headers: getAuthHeaders() });
      console.log('✅ 框架详情加载成功:', res.data);
      setSelectedFramework(res.data);
      setSelectedDimension(null);
      setExpandedCategories(new Set());
    } catch (error: any) {
      console.error('❌ 加载框架详情失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      setError(`加载框架详情失败: ${errorMsg}`);
      alert(`加载失败: ${errorMsg}`);
    } finally {
      setLoadingDetail(false);
    }
  };

  // 重新加载本体论
  const handleReload = async () => {
    try {
      setReloading(true);
      await axios.post('/api/admin/ontology/reload', {}, { headers: getAuthHeaders() });
      await fetchFrameworks();
      await fetchDiagnostics();
      if (selectedFramework) {
        await loadFrameworkDetail(selectedFramework.id);
      }
      alert('本体论已重新加载');
    } catch (error) {
      console.error('重新加载失败:', error);
      alert('重新加载失败');
    } finally {
      setReloading(false);
    }
  };

  // 切换类别展开状态
  const toggleCategory = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  // 过滤维度（搜索功能）
  const filteredCategories = selectedFramework?.categories.map(cat => ({
    ...cat,
    dimensions: cat.dimensions.filter(dim =>
      searchQuery === '' ||
      dim.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dim.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })).filter(cat => cat.dimensions.length > 0);
  const diagnosticFrameworks = new Map(
    (diagnostics?.frameworks || []).map((item) => [item.framework_id, item])
  );
  const issueEntries = Object.entries(diagnostics?.issues || {}).filter(([, items]) => items.length > 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载本体论框架...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部工具栏 */}
      <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">本体论框架浏览器</h1>
          <p className="text-sm text-gray-500 mt-1">
            共 {frameworks.length} 个框架 | 
            {selectedFramework && ` ${selectedFramework.categories.reduce((sum, cat) => sum + cat.dimensions.length, 0)} 个维度`}
          </p>
          {error && (
            <p className="text-sm text-red-500 mt-1">
              ⚠️ {error}
            </p>
          )}
        </div>
        <button
          onClick={handleReload}
          disabled={reloading}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${reloading ? 'animate-spin' : ''}`} />
          重新加载
        </button>
      </div>

      {diagnostics && (
        <div className="border-b bg-white px-6 py-4">
          <div className="mb-3 flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">Ontology 健康</h2>
            <span className={`rounded-full border px-2 py-0.5 text-xs ${
              diagnostics.status === 'ok'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-amber-200 bg-amber-50 text-amber-700'
            }`}>
              {diagnostics.status === 'ok' ? '正常' : '需处理'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-6">
            <Metric label="Framework" value={diagnostics.summary.framework_count} />
            <Metric label="E 维度" value={diagnostics.summary.dimension_count} />
            <Metric label="类型映射" value={diagnostics.summary.project_type_framework_mapping_count} />
            <Metric label="空间层映射" value={diagnostics.summary.spatial_layer_dimension_mapping_count} />
            <Metric label="有知识卡维度" value={diagnostics.summary.approved_card_dimension_count} />
            <Metric label="阻断问题" value={diagnostics.summary.blocking_issue_count} />
          </div>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：框架树形导航 */}
        <div className="w-1/3 bg-white border-r overflow-y-auto">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold mb-3">框架列表</h2>
            <div className="space-y-2">
              {frameworks.map(fw => (
                <FrameworkButton
                  key={fw.id}
                  framework={fw}
                  diagnostic={diagnosticFrameworks.get(fw.id)}
                  selected={selectedFramework?.id === fw.id}
                  loading={loadingDetail}
                  onClick={() => loadFrameworkDetail(fw.id)}
                />
              ))}
            </div>
          </div>

          {/* 类别和维度列表 */}
          {loadingDetail ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-2"></div>
              <p className="text-sm text-gray-500">加载中...</p>
            </div>
          ) : selectedFramework ? (
            <div className="p-4">
              <div className="relative mb-4">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索维度..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="space-y-2">
                {filteredCategories?.map(category => (
                  <div key={category.id}>
                    <button
                      onClick={() => toggleCategory(category.id)}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-100 rounded-lg text-left"
                    >
                      {expandedCategories.has(category.id) ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                      <span className="font-medium">{category.name}</span>
                      <span className="ml-auto text-xs text-gray-500">
                        {category.dimensions.length}
                      </span>
                    </button>

                    {expandedCategories.has(category.id) && (
                      <div className="ml-6 mt-1 space-y-1">
                        {category.dimensions.map((dim, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedDimension(dim)}
                            className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                              selectedDimension === dim
                                ? 'bg-purple-50 text-purple-700'
                                : 'hover:bg-gray-50'
                            }`}
                          >
                            {dim.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {/* 右侧：维度详情 */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedDimension ? (
            <div className="max-w-3xl mx-auto">
              <div className="bg-white rounded-lg shadow-sm p-6 space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    {selectedDimension.name}
                  </h2>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                    描述 (Description)
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    {selectedDimension.description}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                    引导性问题 (Ask Yourself)
                  </h3>
                  <p className="text-gray-600 leading-relaxed italic">
                    {selectedDimension.ask_yourself}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                    示例 (Examples)
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    {selectedDimension.examples}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <OntologyGovernancePanel diagnostics={diagnostics} issueEntries={issueEntries} />
          )}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 font-mono text-lg font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function FrameworkButton({
  framework,
  diagnostic,
  selected,
  loading,
  onClick,
}: {
  framework: Framework;
  diagnostic?: OntologyDiagnosticFramework;
  selected: boolean;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
        selected ? 'bg-purple-100 text-purple-700 font-medium' : 'hover:bg-gray-100'
      } disabled:opacity-50 disabled:cursor-wait`}
    >
      <div className="flex items-center justify-between gap-3">
        <span>{framework.name}</span>
        <span className="text-xs bg-gray-200 px-2 py-1 rounded">
          {framework.total_dimensions}
        </span>
      </div>
      <div className="mt-2 text-xs text-gray-500">
        <div className="font-mono">{framework.id}</div>
        {diagnostic && (
          <div className="mt-1">
            类型 {diagnostic.project_type_ids.length} · 激活包 {diagnostic.activation_pack_ids.length}
          </div>
        )}
      </div>
    </button>
  );
}

function OntologyGovernancePanel({
  diagnostics,
  issueEntries,
}: {
  diagnostics: OntologyDiagnostics | null;
  issueEntries: Array<[string, string[]]>;
}) {
  if (!diagnostics) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <div className="text-center">
          <Search className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">选择一个维度查看详情</p>
        </div>
      </div>
    );
  }

  const dimensionsWithoutCards = diagnostics.issues.dimensions_without_approved_cards || [];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900">E 维度治理覆盖</h2>
        <p className="mt-1 text-sm text-gray-600">
          查看每个本体维度被哪些空间层、激活包和 approved card 支撑。
        </p>
        <div className="mt-4 overflow-hidden rounded border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">维度</th>
                <th className="px-3 py-2">空间层</th>
                <th className="px-3 py-2">激活包</th>
                <th className="px-3 py-2">已审核卡</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {diagnostics.dimensions.map((dimension) => (
                <tr key={dimension.dimension_id}>
                  <td className="px-3 py-2">
                    <div className="font-mono text-xs text-gray-900">{dimension.dimension_id}</div>
                    <div className="mt-1 text-xs text-gray-500">{dimension.name_cn || '-'}</div>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-600">
                    {dimension.spatial_layer_ids.join(', ') || '-'}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-600">
                    {dimension.activation_pack_ids.join(', ') || '-'}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`rounded px-2 py-1 text-xs ${
                      dimension.approved_card_count > 0
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-amber-50 text-amber-700'
                    }`}>
                      {dimension.approved_card_count}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900">治理问题</h2>
        {issueEntries.length === 0 ? (
          <p className="mt-2 text-sm text-emerald-700">当前没有阻断或警告问题。</p>
        ) : (
          <div className="mt-3 space-y-3">
            {issueEntries.map(([key, items]) => (
              <div key={key} className="rounded border border-gray-200 p-3">
                <div className="font-mono text-xs text-gray-700">{key}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {items.slice(0, 12).map((item) => (
                    <span key={item} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        {dimensionsWithoutCards.length > 0 && (
          <p className="mt-3 text-sm text-amber-700">
            缺少知识卡支撑：{dimensionsWithoutCards.join(', ')}
          </p>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900">Framework 引用</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {diagnostics.frameworks.slice(0, 8).map((framework) => (
            <div key={framework.framework_id} className="rounded border border-gray-200 p-3">
              <div className="font-mono text-xs font-semibold text-gray-900">{framework.framework_id}</div>
              <div className="mt-2 text-xs text-gray-600">
                Project Types：{framework.project_type_ids.join(', ') || '-'}
              </div>
              <div className="mt-1 text-xs text-gray-600">
                Activation Packs：{framework.activation_pack_ids.join(', ') || '-'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
