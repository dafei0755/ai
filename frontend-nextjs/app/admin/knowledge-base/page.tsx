'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';  // 🆕 v7.141.3: Real user authentication
import { useMembership } from '@/hooks/useMembership';  // 🆕 v7.141.3: User tier management

interface MilvusStatus {
  status: string;
  enabled: boolean;
  host: string;
  port: number;
  collection_name: string;
  health_details?: {
    status: string;
    collection: string;
    num_entities: number;
  };
  error?: string;
}

interface CollectionStats {
  status: string;
  collection_name: string;
  num_entities: number;
  embedding_dim: number;
  index_type: string;
  metric_type: string;
  is_loaded: boolean;
}

interface SearchResult {
  title: string;
  content: string;
  snippet: string;
  relevance_score: number;
  credibility_score: number;
  reference_number: number;
  source: string;
  metadata: {
    document_type: string;
    tags: string[];
    project_type: string;
    source_file: string;
  };
}

interface SearchTestResponse {
  success: boolean;
  query: string;
  results: SearchResult[];
  total_results: number;
  execution_time: number;
  pipeline_metrics?: {
    query_processing_time: number;
    retrieval_time: number;
    reranking_time: number;
    candidates_count: number;
    filtered_count: number;
  };
}

interface SampleDocument {
  title: string;
  content: string;
  document_type: string;
  tags: string[];
  project_type: string;
  source_file: string;
  owner_type?: string;  // 🆕 v7.141
  owner_id?: string;    // 🆕 v7.141
  visibility?: string;  // 🆕 v7.141
  team_id?: string;     // 🆕 v7.141.2
}

export default function KnowledgeBasePage() {
  // 🆕 v7.141.3: Real user authentication
  const { user, isAuthenticated } = useAuth();
  const { tier, vipLevel, loading: tierLoading } = useMembership();

  const [status, setStatus] = useState<MilvusStatus | null>(null);
  const [stats, setStats] = useState<CollectionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'import' | 'search' | 'samples'>('overview');

  // 文件上传状态
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('设计规范');
  const [projectType, setProjectType] = useState('');
  const [uploading, setUploading] = useState(false);

  // 🆕 v7.141: 用户隔离字段
  // 🆕 v7.141.2: 团队知识库字段
  const [ownerType, setOwnerType] = useState('system');  // "system" | "user" | "team"
  const [ownerVisibility, setOwnerVisibility] = useState('public');  // "public" | "private"
  const [teamId, setTeamId] = useState('');  // 🆕 v7.141.2: 团队ID

  // 批量导入状态
  const [batchJson, setBatchJson] = useState('');
  const [importing, setImporting] = useState(false);

  // 搜索测试状态
  const [searchQuery, setSearchQuery] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  const [searchResult, setSearchResult] = useState<SearchTestResponse | null>(null);
  const [searching, setSearching] = useState(false);

  // 🆕 v7.141: 搜索范围
  const [searchScope, setSearchScope] = useState('all');  // "all" | "system" | "user"

  // 🆕 v7.141.3 - P1-1: 配额检查状态
  const [quotaCheck, setQuotaCheck] = useState<{
    allowed: boolean;
    quota_status?: {
      current_usage: { document_count: number; storage_mb: number };
      quota_limit: { max_documents: number; max_storage_mb: number; max_file_size_mb: number };
      usage_percentage: { documents: number; storage: number };
    };
    file_size_check?: {
      allowed: boolean;
      file_size_mb: number;
      max_file_size_mb: number;
    };
    warnings: string[];
    errors: string[];
    suggestions: string[];
  } | null>(null);
  const [checkingQuota, setCheckingQuota] = useState(false);

  // 示例文档
  const [sampleDocs, setSampleDocs] = useState<SampleDocument[]>([]);
  const [loadingSamples, setLoadingSamples] = useState(false);

  useEffect(() => {
    loadStatus();
    loadStats();
  }, []);

  const loadStatus = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');
      const response = await fetch('/api/admin/milvus/status', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('加载状态失败');

      const data = await response.json();
      setStatus(data);
    } catch (error) {
      console.error('加载状态失败:', error);
      toast.error('加载 Milvus 状态失败');
    }
  };

  const loadStats = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('wp_jwt_token');
      const response = await fetch('/api/admin/milvus/collection/stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('加载统计失败');

      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('加载统计失败:', error);
      toast.error('加载 Collection 统计失败');
    } finally {
      setLoading(false);
    }
  };

  // 🆕 v7.141.3 - P1-1: 配额检查函数（文件选择后调用）
  const checkQuotaBeforeUpload = async (fileSizeBytes?: number) => {
    // 仅对用户知识库和团队知识库进行配额检查
    if (ownerType === 'system') {
      setQuotaCheck(null);
      return;
    }

    // 🆕 v7.141.3: Check if user is authenticated
    if (!isAuthenticated || !user) {
      toast.error('请先登录');
      setQuotaCheck(null);
      return;
    }

    try {
      setCheckingQuota(true);
      const token = localStorage.getItem('wp_jwt_token');

      // 🆕 v7.141.3: Use real user ID and tier
      const userId = ownerType === 'user' ? user.user_id.toString() : teamId;
      const userTier = tier;

      // 构建查询参数
      const params = new URLSearchParams({
        user_id: userId,
        user_tier: userTier,
      });

      if (fileSizeBytes !== undefined) {
        params.append('file_size_bytes', fileSizeBytes.toString());
      }

      const response = await fetch(`/api/admin/milvus/quota/check?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('配额检查失败');
      }

      const data = await response.json();
      setQuotaCheck(data);

      // 显示警告或错误提示
      if (!data.allowed) {
        toast.error(
          <div className="space-y-2">
            <p className="font-bold">⚠️ 无法上传</p>
            <div className="text-xs space-y-1">
              {data.errors.map((err: string, i: number) => (
                <p key={i} className="text-red-600">• {err}</p>
              ))}
            </div>
            <div className="mt-2 text-xs text-blue-600">
              💡 {data.suggestions.join(' 或 ')}
            </div>
          </div>,
          { duration: 6000 }
        );
      } else if (data.warnings.length > 0) {
        toast.warning(
          <div className="space-y-2">
            <p className="font-bold">⚠️ 配额警告</p>
            <div className="text-xs space-y-1">
              {data.warnings.map((warn: string, i: number) => (
                <p key={i} className="text-yellow-600">• {warn}</p>
              ))}
            </div>
            {data.suggestions.length > 0 && (
              <div className="mt-2 text-xs text-blue-600">
                💡 {data.suggestions[0]}
              </div>
            )}
          </div>,
          { duration: 5000 }
        );
      }

    } catch (error) {
      console.error('配额检查失败:', error);
      // 配额检查失败不阻止上传，仅记录日志
      setQuotaCheck(null);
    } finally {
      setCheckingQuota(false);
    }
  };

  // 🆕 v7.141.3 - P1-1: 文件选择处理（自动触发配额检查）
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      setUploadFile(null);
      setQuotaCheck(null);
      return;
    }

    setUploadFile(file);

    // 自动触发配额检查（包含文件大小）
    await checkQuotaBeforeUpload(file.size);
  };

  const handleFileUpload = async () => {
    if (!uploadFile) {
      toast.error('请选择文件');
      return;
    }

    // 🆕 v7.141.3: Check authentication
    if (!isAuthenticated || !user) {
      toast.error('请先登录');
      return;
    }

    // 🆕 v7.141.3 - P1-1: 配额检查前置验证
    if (quotaCheck && !quotaCheck.allowed) {
      toast.error(
        <div className="space-y-2">
          <p className="font-bold">⚠️ 无法上传</p>
          <p className="text-sm">配额不足，请清理文档或升级会员等级</p>
          <div className="text-xs space-y-1">
            {quotaCheck.errors.map((err: string, i: number) => (
              <p key={i} className="text-red-600">• {err}</p>
            ))}
          </div>
        </div>,
        { duration: 5000 }
      );
      return;
    }

    try {
      setUploading(true);
      const token = localStorage.getItem('wp_jwt_token');
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('document_type', documentType);
      formData.append('project_type', projectType);

      // 🆕 v7.141: 添加用户隔离参数
      // 🆕 v7.141.2: 添加团队知识库参数
      // 🆕 v7.141.3: 使用真实用户ID和会员等级
      const userId = ownerType === 'user' ? user.user_id.toString() : (ownerType === 'team' ? teamId : 'public');
      const userTier = tier;

      formData.append('owner_type', ownerType);
      formData.append('owner_id', userId);
      formData.append('visibility', ownerVisibility);
      formData.append('team_id', ownerType === 'team' ? teamId : '');
      formData.append('user_tier', userTier);

      const response = await fetch('/api/admin/milvus/import/file', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      // 🆕 v7.141.3: 配额超限错误处理
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);

        // 处理配额超限错误（HTTP 403）
        if (response.status === 403 && errorData?.detail?.error === 'quota_exceeded') {
          const { detail } = errorData;
          const usage = detail.current_usage;
          const limit = detail.quota_limit;

          toast.error(
            <div className="space-y-2">
              <p className="font-bold">⚠️ 配额已满</p>
              <p className="text-sm">{detail.message}</p>
              <div className="text-xs space-y-1">
                {detail.errors.map((err: string, i: number) => (
                  <p key={i} className="text-red-600">• {err}</p>
                ))}
                <p className="mt-2 font-semibold">当前使用量:</p>
                <p>文档数量: {usage.document_count}/{limit.max_documents}</p>
                <p>存储空间: {usage.storage_mb}/{limit.max_storage_mb} MB</p>
              </div>
              <div className="mt-2 text-xs text-blue-600">
                💡 {detail.suggestions.join(' 或 ')}
              </div>
            </div>,
            { duration: 8000 }
          );
          return;
        }

        // 处理文件大小超限错误（HTTP 413）
        if (response.status === 413 && errorData?.detail?.error === 'file_size_exceeded') {
          const { detail } = errorData;
          toast.error(
            <div className="space-y-2">
              <p className="font-bold">⚠️ 文件大小超限</p>
              <p className="text-sm">{detail.message}</p>
              <div className="text-xs">
                <p>文件大小: {detail.file_size_mb} MB</p>
                <p>最大限制: {detail.max_file_size_mb} MB</p>
                <p className="text-gray-600 mt-1">会员等级: {detail.user_tier}</p>
              </div>
              <p className="mt-2 text-xs text-blue-600">💡 升级会员等级以提升单文件大小限制</p>
            </div>,
            { duration: 6000 }
          );
          return;
        }

        // 其他错误
        throw new Error(errorData?.message || '文件上传失败');
      }

      const data = await response.json();
      toast.success(data.message || '文件导入成功');

      // 重新加载统计
      await loadStats();

      // 清空表单
      setUploadFile(null);
      setProjectType('');
    } catch (error) {
      console.error('文件上传失败:', error);
      toast.error(error instanceof Error ? error.message : '文件上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleBatchImport = async () => {
    if (!batchJson.trim()) {
      toast.error('请输入 JSON 数据');
      return;
    }

    try {
      setImporting(true);
      const token = localStorage.getItem('wp_jwt_token');

      // 验证 JSON 格式
      let documents;
      try {
        documents = JSON.parse(batchJson);
      } catch (e) {
        toast.error('JSON 格式错误');
        return;
      }

      const response = await fetch('/api/admin/milvus/import/batch', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(documents)
      });

      if (!response.ok) throw new Error('批量导入失败');

      const data = await response.json();
      toast.success(data.message || '批量导入成功');

      // 重新加载统计
      await loadStats();

      // 清空表单
      setBatchJson('');
    } catch (error) {
      console.error('批量导入失败:', error);
      toast.error('批量导入失败');
    } finally {
      setImporting(false);
    }
  };

  const handleSearchTest = async () => {
    if (!searchQuery.trim()) {
      toast.error('请输入搜索查询');
      return;
    }

    try {
      setSearching(true);
      const token = localStorage.getItem('wp_jwt_token');

      // 🆕 v7.141.3: Use real user ID if searching user scope
      const realUserId = user ? user.user_id.toString() : 'user_mock_123';

      const response = await fetch('/api/admin/milvus/search/test', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: searchQuery,
          max_results: maxResults,
          user_id: searchScope === 'user' ? realUserId : undefined,
          team_id: searchScope === 'team' ? teamId : undefined,
          search_scope: searchScope
        })
      });

      if (!response.ok) throw new Error('搜索测试失败');

      const data = await response.json();
      setSearchResult(data);
      toast.success(`找到 ${data.total_results} 个结果`);
    } catch (error) {
      console.error('搜索测试失败:', error);
      toast.error('搜索测试失败');
    } finally {
      setSearching(false);
    }
  };

  const loadSampleDocuments = async () => {
    try {
      setLoadingSamples(true);
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch('/api/admin/milvus/documents/sample?limit=10', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('加载示例文档失败');

      const data = await response.json();
      setSampleDocs(data.documents || []);
    } catch (error) {
      console.error('加载示例文档失败:', error);
      toast.error('加载示例文档失败');
    } finally {
      setLoadingSamples(false);
    }
  };

  const clearCollection = async () => {
    if (!confirm('⚠️ 警告：此操作将清空所有知识库数据，且不可恢复！确定要继续吗？')) {
      return;
    }

    if (!confirm('请再次确认：真的要清空所有数据吗？')) {
      return;
    }

    try {
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch('/api/admin/milvus/collection/clear', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('清空失败');

      const data = await response.json();
      toast.success(data.message || 'Collection 已清空');

      // 重新加载统计
      await loadStats();
    } catch (error) {
      console.error('清空失败:', error);
      toast.error('清空失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Milvus 知识库管理</h1>
        <p className="text-gray-600 mt-2">管理向量数据库知识库的导入、搜索和监控</p>
      </div>

      {/* 服务状态横幅 */}
      {status && (
        <div className={`mb-6 p-4 rounded-lg border ${
          status.status === 'healthy'
            ? 'bg-green-50 border-green-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">
                {status.status === 'healthy' ? '✅ Milvus 服务正常' : '❌ Milvus 服务异常'}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                服务地址: {status.host}:{status.port} | Collection: {status.collection_name}
              </p>
              {status.health_details && (
                <p className="text-sm text-gray-600">
                  文档数量: {status.health_details.num_entities}
                </p>
              )}
            </div>
            <button
              onClick={loadStatus}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              🔄 刷新状态
            </button>
          </div>
        </div>
      )}

      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">文档总数</div>
            <div className="text-2xl font-bold text-blue-600">{stats.num_entities}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">向量维度</div>
            <div className="text-2xl font-bold text-purple-600">{stats.embedding_dim}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">索引类型</div>
            <div className="text-lg font-bold text-green-600">{stats.index_type}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">相似度度量</div>
            <div className="text-lg font-bold text-orange-600">{stats.metric_type}</div>
          </div>
        </div>
      )}

      {/* 标签页切换 */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <TabButton
              active={activeTab === 'overview'}
              onClick={() => setActiveTab('overview')}
              icon="📊"
              label="概览"
            />
            <TabButton
              active={activeTab === 'import'}
              onClick={() => setActiveTab('import')}
              icon="📤"
              label="数据导入"
            />
            <TabButton
              active={activeTab === 'search'}
              onClick={() => setActiveTab('search')}
              icon="🔍"
              label="搜索测试"
            />
            <TabButton
              active={activeTab === 'samples'}
              onClick={() => {
                setActiveTab('samples');
                if (sampleDocs.length === 0) {
                  loadSampleDocuments();
                }
              }}
              icon="📄"
              label="示例文档"
            />
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'overview' && (
            <OverviewTab stats={stats} onClearCollection={clearCollection} />
          )}

          {activeTab === 'import' && (
            <ImportTab
              uploadFile={uploadFile}
              setUploadFile={setUploadFile}
              documentType={documentType}
              setDocumentType={setDocumentType}
              projectType={projectType}
              setProjectType={setProjectType}
              uploading={uploading}
              onUpload={handleFileUpload}
              batchJson={batchJson}
              setBatchJson={setBatchJson}
              importing={importing}
              onImport={handleBatchImport}
              ownerType={ownerType}           // 🆕 v7.141
              setOwnerType={setOwnerType}     // 🆕 v7.141
              ownerVisibility={ownerVisibility} // 🆕 v7.141
              setOwnerVisibility={setOwnerVisibility} // 🆕 v7.141
              teamId={teamId}                 // 🆕 v7.141.2
              setTeamId={setTeamId}           // 🆕 v7.141.2
              quotaCheck={quotaCheck}         // 🆕 v7.141.3 - P1-1
              checkingQuota={checkingQuota}   // 🆕 v7.141.3 - P1-1
              handleFileSelect={handleFileSelect} // 🆕 v7.141.3 - P1-1
            />
          )}

          {activeTab === 'search' && (
            <SearchTab
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              maxResults={maxResults}
              setMaxResults={setMaxResults}
              searching={searching}
              onSearch={handleSearchTest}
              searchResult={searchResult}
              searchScope={searchScope}         // 🆕 v7.141
              setSearchScope={setSearchScope}   // 🆕 v7.141
              teamId={teamId}                   // 🆕 v7.141.2
              setTeamId={setTeamId}             // 🆕 v7.141.2
            />
          )}

          {activeTab === 'samples' && (
            <SamplesTab
              samples={sampleDocs}
              loading={loadingSamples}
              onReload={loadSampleDocuments}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 辅助组件
// ============================================================================

function TabButton({ active, onClick, icon, label }: {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`py-4 px-6 border-b-2 font-medium text-sm ${
        active
          ? 'border-blue-500 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
      }`}
    >
      {icon} {label}
    </button>
  );
}

function OverviewTab({ stats, onClearCollection }: {
  stats: CollectionStats | null;
  onClearCollection: () => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold mb-4">Collection 详情</h2>
        {stats ? (
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Collection 名称:</span>
              <span className="font-mono font-semibold">{stats.collection_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">文档总数:</span>
              <span className="font-semibold">{stats.num_entities}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">向量维度:</span>
              <span className="font-semibold">{stats.embedding_dim}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">索引类型:</span>
              <span className="font-semibold">{stats.index_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">相似度度量:</span>
              <span className="font-semibold">{stats.metric_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">加载状态:</span>
              <span className={`font-semibold ${stats.is_loaded ? 'text-green-600' : 'text-red-600'}`}>
                {stats.is_loaded ? '已加载' : '未加载'}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">无法加载 Collection 信息</p>
        )}
      </div>

      <div>
        <h2 className="text-lg font-bold mb-4 text-red-600">⚠️ 危险操作</h2>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700 mb-4">
            清空 Collection 将删除所有向量数据，此操作不可恢复！
          </p>
          <button
            onClick={onClearCollection}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            🗑️ 清空 Collection
          </button>
        </div>
      </div>
    </div>
  );
}

function ImportTab({
  uploadFile,
  setUploadFile,
  documentType,
  setDocumentType,
  projectType,
  setProjectType,
  uploading,
  onUpload,
  batchJson,
  setBatchJson,
  importing,
  onImport,
  ownerType,           // 🆕 v7.141
  setOwnerType,        // 🆕 v7.141
  ownerVisibility,     // 🆕 v7.141
  setOwnerVisibility,  // 🆕 v7.141
  teamId,              // 🆕 v7.141.2
  setTeamId,           // 🆕 v7.141.2
  quotaCheck,          // 🆕 v7.141.3 - P1-1
  checkingQuota,       // 🆕 v7.141.3 - P1-1
  handleFileSelect     // 🆕 v7.141.3 - P1-1
}: any) {
  return (
    <div className="space-y-6">
      {/* 文件上传 */}
      <div>
        <h2 className="text-lg font-bold mb-4">📤 文件上传</h2>
        <div className="bg-gray-50 rounded-lg p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              选择文件 (支持 .txt, .md, .json)
            </label>
            <input
              type="file"
              accept=".txt,.md,.json"
              onChange={handleFileSelect}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
            {uploadFile && (
              <div className="mt-2 space-y-1">
                <p className="text-sm text-gray-600">
                  已选择: {uploadFile.name} ({(uploadFile.size / 1024).toFixed(2)} KB)
                </p>
                {/* 🆕 v7.141.3 - P1-1: 配额检查状态显示 */}
                {checkingQuota && (
                  <p className="text-sm text-blue-600 animate-pulse">
                    ⏳ 正在检查配额...
                  </p>
                )}
                {quotaCheck && (
                  <div className="text-xs space-y-1">
                    {quotaCheck.allowed ? (
                      <div className="text-green-600">
                        ✅ 配额检查通过
                        {quotaCheck.quota_status && (
                          <span className="ml-2">
                            ({quotaCheck.quota_status.usage_percentage.documents.toFixed(1)}% 使用中)
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="text-red-600">
                        ❌ 配额不足，无法上传
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              文档类型
            </label>
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="设计规范">设计规范</option>
              <option value="案例库">案例库</option>
              <option value="技术知识">技术知识</option>
              <option value="文档">文档</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              项目类型 (可选)
            </label>
            <input
              type="text"
              value={projectType}
              onChange={(e) => setProjectType(e.target.value)}
              placeholder="如: residential, commercial"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* 🆕 v7.141: 知识库类型选择 */}
          {/* 🆕 v7.141.2: 添加团队知识库选项 */}
          <div className="border-t border-gray-200 pt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              知识库类型
            </label>
            <select
              value={ownerType}
              onChange={(e) => setOwnerType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="system">📚 公共知识库（所有用户可见）</option>
              <option value="user">🔒 私有知识库（仅自己可见）</option>
              <option value="team">👥 团队知识库（团队成员可见）</option>
            </select>
          </div>

          {/* 🆕 v7.141.2: 团队ID输入 (仅团队库显示) */}
          {ownerType === 'team' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                团队ID
              </label>
              <input
                type="text"
                value={teamId}
                onChange={(e) => setTeamId(e.target.value)}
                placeholder="输入团队ID（如: team_001）"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              />
              <p className="text-xs text-gray-500 mt-1">
                团队成员将可以访问此文档
              </p>
            </div>
          )}

          {/* 🆕 v7.141: 可见性选择 (仅私有库显示) */}
          {ownerType === 'user' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                可见性
              </label>
              <select
                value={ownerVisibility}
                onChange={(e) => setOwnerVisibility(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              >
                <option value="public">公开（其他用户可见）</option>
                <option value="private">私有（仅自己可见）</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {ownerVisibility === 'public' ? '✅ 设置为公开后，所有用户都可以搜索到此文档' : '🔒 设置为私有后，只有您自己可以看到此文档'}
              </p>
            </div>
          )}

          <button
            onClick={onUpload}
            disabled={!uploadFile || uploading || (quotaCheck && !quotaCheck.allowed)}
            className={`w-full px-4 py-2 rounded-lg ${
              uploadFile && !uploading && (!quotaCheck || quotaCheck.allowed)
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {uploading ? '上传中...' : (quotaCheck && !quotaCheck.allowed ? '配额不足' : '开始上传')}
          </button>
        </div>
      </div>

      {/* 批量导入 */}
      <div>
        <h2 className="text-lg font-bold mb-4">📋 批量导入 (JSON)</h2>
        <div className="bg-gray-50 rounded-lg p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              JSON 数据 (数组格式)
            </label>
            <textarea
              value={batchJson}
              onChange={(e) => setBatchJson(e.target.value)}
              placeholder={`[\n  {\n    "title": "文档标题",\n    "content": "文档内容",\n    "document_type": "设计规范",\n    "tags": ["标签1", "标签2"],\n    "project_type": "residential"\n  }\n]`}
              rows={12}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg font-mono text-sm"
            />
          </div>

          <button
            onClick={onImport}
            disabled={!batchJson.trim() || importing}
            className={`w-full px-4 py-2 rounded-lg ${
              batchJson.trim() && !importing
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {importing ? '导入中...' : '批量导入'}
          </button>
        </div>
      </div>
    </div>
  );
}

function SearchTab({
  searchQuery,
  setSearchQuery,
  maxResults,
  setMaxResults,
  searching,
  onSearch,
  searchResult,
  searchScope,       // 🆕 v7.141
  setSearchScope,    // 🆕 v7.141
  teamId,            // 🆕 v7.141.2
  setTeamId          // 🆕 v7.141.2
}: any) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold mb-4">🔍 搜索测试</h2>
        <div className="bg-gray-50 rounded-lg p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              搜索查询
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="输入搜索关键词..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              最大结果数
            </label>
            <input
              type="number"
              value={maxResults}
              onChange={(e) => setMaxResults(parseInt(e.target.value))}
              min={1}
              max={50}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* 🆕 v7.141: 搜索范围选择 */}
          {/* 🆕 v7.141.2: 添加团队搜索选项 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              搜索范围
            </label>
            <select
              value={searchScope}
              onChange={(e) => setSearchScope(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="all">📚 全部（公共 + 私有 + 共享 + 团队）</option>
              <option value="system">🌐 仅公共知识库</option>
              <option value="user">🔒 仅我的私有库</option>
              <option value="team">👥 仅团队知识库</option>
            </select>
          </div>

          {/* 🆕 v7.141.2: 团队ID输入 (仅团队搜索显示) */}
          {searchScope === 'team' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                团队ID
              </label>
              <input
                type="text"
                value={teamId}
                onChange={(e) => setTeamId(e.target.value)}
                placeholder="输入团队ID（如: team_001）"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          )}

          <button
            onClick={onSearch}
            disabled={!searchQuery.trim() || searching}
            className={`w-full px-4 py-2 rounded-lg ${
              searchQuery.trim() && !searching
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {searching ? '搜索中...' : '开始搜索'}
          </button>
        </div>
      </div>

      {/* 搜索结果 */}
      {searchResult && (
        <div>
          <h2 className="text-lg font-bold mb-4">搜索结果</h2>

          {/* Pipeline 指标 */}
          {searchResult.pipeline_metrics && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold mb-2">⚡ Pipeline 指标</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                <div>
                  <span className="text-gray-600">总耗时:</span>
                  <span className="ml-2 font-semibold">{(searchResult.execution_time * 1000).toFixed(0)}ms</span>
                </div>
                <div>
                  <span className="text-gray-600">查询处理:</span>
                  <span className="ml-2 font-semibold">{(searchResult.pipeline_metrics.query_processing_time * 1000).toFixed(0)}ms</span>
                </div>
                <div>
                  <span className="text-gray-600">向量检索:</span>
                  <span className="ml-2 font-semibold">{(searchResult.pipeline_metrics.retrieval_time * 1000).toFixed(0)}ms</span>
                </div>
                <div>
                  <span className="text-gray-600">重排序:</span>
                  <span className="ml-2 font-semibold">{(searchResult.pipeline_metrics.reranking_time * 1000).toFixed(0)}ms</span>
                </div>
                <div>
                  <span className="text-gray-600">候选文档:</span>
                  <span className="ml-2 font-semibold">{searchResult.pipeline_metrics.candidates_count}</span>
                </div>
                <div>
                  <span className="text-gray-600">最终结果:</span>
                  <span className="ml-2 font-semibold">{searchResult.pipeline_metrics.filtered_count}</span>
                </div>
              </div>
            </div>
          )}

          {/* 结果列表 */}
          <div className="space-y-4">
            {searchResult.results.map((result: SearchResult, index: number) => (
              <div key={index} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">{result.title}</h3>
                  <div className="flex gap-2">
                    <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                      相似度: {(result.relevance_score * 100).toFixed(1)}%
                    </span>
                    <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                      可信度: {(result.credibility_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-700 mb-3">{result.snippet}</p>
                <div className="flex gap-2 text-xs text-gray-500">
                  <span className="px-2 py-1 bg-gray-100 rounded">{result.metadata.document_type}</span>
                  {result.metadata.project_type && (
                    <span className="px-2 py-1 bg-gray-100 rounded">{result.metadata.project_type}</span>
                  )}
                  {result.metadata.tags.map((tag, i) => (
                    <span key={i} className="px-2 py-1 bg-gray-100 rounded">{tag}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {searchResult.results.length === 0 && (
            <p className="text-center text-gray-500 py-8">未找到相关文档</p>
          )}
        </div>
      )}
    </div>
  );
}

function SamplesTab({ samples, loading, onReload }: {
  samples: SampleDocument[];
  loading: boolean;
  onReload: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">📄 示例文档</h2>
        <button
          onClick={onReload}
          disabled={loading}
          className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
        >
          🔄 刷新
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      ) : samples.length > 0 ? (
        <div className="space-y-4">
          {samples.map((doc, index) => (
            <div key={index} className="bg-white border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900 mb-2">{doc.title}</h3>
              <p className="text-sm text-gray-700 mb-3 line-clamp-3">{doc.content}</p>
              <div className="flex gap-2 text-xs text-gray-500">
                {/* 🆕 v7.141: 显示所有者标签 */}
                {/* 🆕 v7.141.2: 添加团队标签 */}
                {doc.owner_type === 'system' ? (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">📚 公共</span>
                ) : doc.owner_type === 'team' ? (
                  <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">👥 团队</span>
                ) : (
                  <span className="px-2 py-1 bg-green-100 text-green-700 rounded">
                    {doc.visibility === 'public' ? '🔓 共享' : '🔒 私有'}
                  </span>
                )}
                <span className="px-2 py-1 bg-gray-100 rounded">{doc.document_type}</span>
                {doc.project_type && (
                  <span className="px-2 py-1 bg-gray-100 rounded">{doc.project_type}</span>
                )}
                {doc.tags.map((tag, i) => (
                  <span key={i} className="px-2 py-1 bg-gray-100 rounded">{tag}</span>
                ))}
                <span className="px-2 py-1 bg-gray-100 rounded">来源: {doc.source_file}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-center text-gray-500 py-8">暂无文档数据</p>
      )}
    </div>
  );
}
