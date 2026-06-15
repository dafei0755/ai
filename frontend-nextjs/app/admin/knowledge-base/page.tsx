'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';  // 🆕 v7.141.3: Real user authentication
import {
  ApprovedKnowledgeCardsPanel,
  type ApprovedKnowledgeCard,
  type ApprovedKnowledgeCardSummary,
} from './ApprovedKnowledgeCardsPanel';
import {
  PackagesTab,
  type DocumentTypeStat,
  type KnowledgePackage,
  type SampleDocument,
} from './KnowledgePackagesPanel';

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
    tags: string[] | string;
    project_type: string;
    package_id?: string;
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

type AssetDraftMode = 'document' | 'observation' | 'directory';

interface AssetDraft {
  schema_version: string;
  draft_id: string;
  review_status: string;
  source_ref: {
    source_type: string;
    source_path?: string;
    observation_id?: string;
  };
  asset_card_candidate: {
    title: string;
    summary: string;
    body_markdown: string;
    language: string;
  };
  classification_candidate?: {
    project_type?: string;
    subdomain_id?: string;
    activation_pack_id?: string;
    confidence?: number;
    promotion_policy?: string;
    reasons?: string[];
  };
  ontology_binding_candidate?: {
    ontology_dimension_ids?: string[];
    confidence?: string;
    promotion_policy?: string;
    reasons?: string[];
  };
  knowledge_binding_candidate?: {
    package_ids?: string[];
    allowed_use?: string[];
    not_allowed_use?: string[];
    confidence?: string;
    promotion_policy?: string;
    reasons?: string[];
  };
  evidence_map_candidate?: {
    source_observations?: string[];
    local_source_paths?: string[];
    cleaning_reports?: string[];
    evidence_strength?: string;
    limitations?: string[];
  };
  risk_flags: string[];
  missing_fields: string[];
  generation_notes: string[];
  created_at: string;
}

interface AssetDraftDirectoryResult {
  total_items: number;
  generated_count: number;
  skipped_count: number;
  failed_count: number;
  items: Array<{
    source_path: string;
    draft_id: string | null;
    status: string;
    reason: string;
    warnings: string[];
  }>;
}

function normalizeTags(tags: string[] | string | null | undefined): string[] {
  if (Array.isArray(tags)) {
    return tags.filter(Boolean).map(String);
  }
  if (!tags) {
    return [];
  }
  const text = String(tags).trim();
  if (!text) {
    return [];
  }
  try {
    const parsed = JSON.parse(text.replace(/'/g, '"'));
    if (Array.isArray(parsed)) {
      return parsed.filter(Boolean).map(String);
    }
  } catch {
    // Fall through to comma splitting for Milvus array-string output.
  }
  return text
    .replace(/^\[/, '')
    .replace(/\]$/, '')
    .split(',')
    .map((tag) => tag.trim().replace(/^['"]|['"]$/g, ''))
    .filter(Boolean);
}

export default function KnowledgeBasePage() {
  const { user, isAuthenticated } = useAuth();
  const knowledgeAccessTier = 'internal';

  const [status, setStatus] = useState<MilvusStatus | null>(null);
  const [stats, setStats] = useState<CollectionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'packages' | 'approved-cards' | 'drafts' | 'import' | 'search' | 'samples'>('overview');

  // 文件上传状态
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('设计规范');
  const [projectType, setProjectType] = useState('');
  const [packageId, setPackageId] = useState('');
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
  const [searchPackageId, setSearchPackageId] = useState('');
  const [searchProjectType, setSearchProjectType] = useState('');

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
  const [packages, setPackages] = useState<KnowledgePackage[]>([]);
  const [loadingPackages, setLoadingPackages] = useState(false);
  const [approvedCards, setApprovedCards] = useState<ApprovedKnowledgeCard[]>([]);
  const [approvedCardSummary, setApprovedCardSummary] = useState<ApprovedKnowledgeCardSummary | undefined>(undefined);
  const [loadingApprovedCards, setLoadingApprovedCards] = useState(false);
  const [importingSamples, setImportingSamples] = useState(false);
  const [packageDocs, setPackageDocs] = useState<SampleDocument[]>([]);
  const [loadingPackageDocs, setLoadingPackageDocs] = useState(false);
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeStat[]>([]);
  const [selectedDocumentType, setSelectedDocumentType] = useState('');
  const [showUnboundDocs, setShowUnboundDocs] = useState(false);
  const [countsAvailable, setCountsAvailable] = useState(true);
  const [packageCountError, setPackageCountError] = useState('');
  const [unboundDocumentCount, setUnboundDocumentCount] = useState(0);

  // 方案高参资产草稿
  const [assetDraftMode, setAssetDraftMode] = useState<AssetDraftMode>('document');
  const [assetDraftSourcePath, setAssetDraftSourcePath] = useState('');
  const [assetDraftObservationId, setAssetDraftObservationId] = useState('');
  const [assetDraftObservationRoot, setAssetDraftObservationRoot] = useState('');
  const [assetDraftDirectoryPath, setAssetDraftDirectoryPath] = useState('');
  const [generatingAssetDraft, setGeneratingAssetDraft] = useState(false);
  const [assetDraft, setAssetDraft] = useState<AssetDraft | null>(null);
  const [assetDraftDirectoryResult, setAssetDraftDirectoryResult] = useState<AssetDraftDirectoryResult | null>(null);

  useEffect(() => {
    loadStatus();
    loadStats();
    loadKnowledgePackages();
    loadApprovedKnowledgeCards();
    loadDocumentTypes();
  }, []);

  const loadStatus = async () => {
    try {
      const token = localStorage.getItem('app_auth_token');
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
      const token = localStorage.getItem('app_auth_token');
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
      const token = localStorage.getItem('app_auth_token');

      const userId = ownerType === 'user' ? user.user_id.toString() : teamId;
      const userTier = knowledgeAccessTier;

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
          <p className="text-sm">上传条件不满足，请检查文件或知识库归属设置</p>
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
      const token = localStorage.getItem('app_auth_token');
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('document_type', documentType);
      formData.append('project_type', projectType);
      formData.append('package_id', packageId);

      const userId = ownerType === 'user' ? user.user_id.toString() : (ownerType === 'team' ? teamId : 'public');
      const userTier = knowledgeAccessTier;

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
                <p className="text-gray-600 mt-1">访问档位: {detail.user_tier}</p>
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
      setPackageId('');
      await loadKnowledgePackages();
      await loadDocumentTypes();
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
      const token = localStorage.getItem('app_auth_token');

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
      await loadKnowledgePackages();
      await loadDocumentTypes();
      setPackageDocs([]);
      await loadKnowledgePackages();
      await loadDocumentTypes();

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
      const token = localStorage.getItem('app_auth_token');

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
          search_scope: searchScope,
          knowledge_packages: searchPackageId ? [searchPackageId] : undefined,
          project_type: searchProjectType || undefined
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

  const handleGenerateAssetDraft = async () => {
    const endpointByMode: Record<AssetDraftMode, string> = {
      document: '/api/v1/advisor-knowledge/asset-drafts/from-document',
      observation: '/api/v1/advisor-knowledge/asset-drafts/from-observation',
      directory: '/api/v1/advisor-knowledge/asset-drafts/from-directory',
    };
    const payloadByMode: Record<AssetDraftMode, Record<string, string>> = {
      document: { source_path: assetDraftSourcePath.trim() },
      observation: {
        observation_id: assetDraftObservationId.trim(),
        observation_root: assetDraftObservationRoot.trim(),
      },
      directory: { directory_path: assetDraftDirectoryPath.trim() },
    };
    const payload = payloadByMode[assetDraftMode];
    const hasMissingInput = Object.values(payload).some((value) => !value);
    if (hasMissingInput) {
      toast.error('请补全当前模式所需路径或 observation 信息');
      return;
    }

    try {
      setGeneratingAssetDraft(true);
      setAssetDraft(null);
      setAssetDraftDirectoryResult(null);
      const response = await fetch(endpointByMode[assetDraftMode], {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.detail || '生成资产草稿失败');
      }
      if (assetDraftMode === 'directory') {
        setAssetDraftDirectoryResult(data);
        toast.success(`生成 ${data.generated_count || 0} 条草稿，跳过 ${data.skipped_count || 0} 项`);
      } else {
        setAssetDraft(data);
        toast.success('资产草稿已生成，需人工复核后才能入队上传');
      }
    } catch (error) {
      console.error('生成资产草稿失败:', error);
      toast.error(error instanceof Error ? error.message : '生成资产草稿失败');
    } finally {
      setGeneratingAssetDraft(false);
    }
  };

  const loadSampleDocuments = async () => {
    try {
      setLoadingSamples(true);
      const token = localStorage.getItem('app_auth_token');

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

  const loadKnowledgePackages = async () => {
    try {
      setLoadingPackages(true);
      const token = localStorage.getItem('app_auth_token');
      const response = await fetch('/api/admin/milvus/knowledge-packages', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('加载知识包失败');
      const data = await response.json();
      const nextPackages = [...(data.packages || [])].sort((a, b) => {
        const countDiff = (b.document_count || 0) - (a.document_count || 0);
        const cardDiff = (b.approved_card_count || 0) - (a.approved_card_count || 0);
        return countDiff || cardDiff || a.package_id.localeCompare(b.package_id);
      });
      setPackages(nextPackages);
      setCountsAvailable(data.counts_available !== false);
      setPackageCountError(data.count_error || '');
      setUnboundDocumentCount(data.unbound_document_count || 0);
    } catch (error) {
      console.error('加载知识包失败:', error);
      toast.error('加载知识包失败');
    } finally {
      setLoadingPackages(false);
    }
  };

  const loadApprovedKnowledgeCards = async () => {
    try {
      setLoadingApprovedCards(true);
      const token = localStorage.getItem('app_auth_token');
      const response = await fetch('/api/admin/milvus/approved-knowledge-cards', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('加载已审核知识卡失败');
      const data = await response.json();
      setApprovedCards(data.cards || []);
      setApprovedCardSummary(data.summary);
    } catch (error) {
      console.error('加载已审核知识卡失败:', error);
      toast.error('加载已审核知识卡失败');
    } finally {
      setLoadingApprovedCards(false);
    }
  };

  const loadDocumentTypes = async (scopePackageId = '', unbound = false) => {
    try {
      const token = localStorage.getItem('app_auth_token');
      const params = new URLSearchParams();
      if (scopePackageId) params.set('package_id', scopePackageId);
      if (unbound) params.set('unbound', 'true');
      const response = await fetch(`/api/admin/milvus/document-types?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('加载文档类型失败');
      const data = await response.json();
      setDocumentTypes(data.document_types || []);
    } catch (error) {
      console.error('加载文档类型失败:', error);
      toast.error('加载文档类型失败');
    }
  };

  const loadPackageDocuments = async (scopePackageId: string, docType = '', unbound = false) => {
    try {
      setLoadingPackageDocs(true);
      const token = localStorage.getItem('app_auth_token');
      const params = new URLSearchParams({ limit: '100' });
      if (scopePackageId) params.set('package_id', scopePackageId);
      if (docType) params.set('document_type', docType);
      if (unbound) params.set('unbound', 'true');
      const response = await fetch(`/api/admin/milvus/documents/sample?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('加载知识包文档失败');
      const data = await response.json();
      setPackageDocs(data.documents || []);
    } catch (error) {
      console.error('加载知识包文档失败:', error);
      toast.error('加载知识包文档失败');
    } finally {
      setLoadingPackageDocs(false);
    }
  };

  const openKnowledgePackage = async (scopePackageId: string) => {
    setShowUnboundDocs(false);
    setPackageId(scopePackageId);
    setSelectedDocumentType('');
    await Promise.all([
      loadPackageDocuments(scopePackageId),
      loadDocumentTypes(scopePackageId),
    ]);
  };

  const selectPackageDocumentType = async (docType: string) => {
    setSelectedDocumentType(docType);
    await loadPackageDocuments(packageId, docType, showUnboundDocs);
  };

  const closeKnowledgePackage = async () => {
    setShowUnboundDocs(false);
    setPackageId('');
    setSelectedDocumentType('');
    setPackageDocs([]);
    await loadDocumentTypes();
  };

  const openUnboundDocuments = async () => {
    setShowUnboundDocs(true);
    setPackageId('');
    setSelectedDocumentType('');
    await Promise.all([
      loadPackageDocuments('', '', true),
      loadDocumentTypes('', true),
    ]);
  };

  const importSampleKnowledge = async () => {
    try {
      setImportingSamples(true);
      const token = localStorage.getItem('app_auth_token');
      const response = await fetch('/api/admin/milvus/knowledge-packages/import-samples', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(packageId ? [packageId] : null)
      });
      if (!response.ok) throw new Error('导入示范数据失败');
      const data = await response.json();
      toast.success(data.message || '示范数据导入成功');
      await loadStats();
      await loadKnowledgePackages();
      await loadDocumentTypes(packageId, showUnboundDocs);
      if (packageId || showUnboundDocs) {
        await loadPackageDocuments(packageId, selectedDocumentType, showUnboundDocs);
      }
      await loadSampleDocuments();
    } catch (error) {
      console.error('导入示范数据失败:', error);
      toast.error('导入示范数据失败');
    } finally {
      setImportingSamples(false);
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
      const token = localStorage.getItem('app_auth_token');

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
              active={activeTab === 'packages'}
              onClick={() => {
                setActiveTab('packages');
                loadKnowledgePackages();
              }}
              icon="📦"
              label="知识包"
            />
            <TabButton
              active={activeTab === 'approved-cards'}
              onClick={() => {
                setActiveTab('approved-cards');
                loadApprovedKnowledgeCards();
              }}
              icon="✅"
              label="已审核知识卡"
            />
            <TabButton
              active={activeTab === 'drafts'}
              onClick={() => setActiveTab('drafts')}
              icon="🧩"
              label="资产草稿"
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

          {activeTab === 'packages' && (
            <PackagesTab
              packages={packages}
              loading={loadingPackages}
              selectedPackageId={packageId}
              setSelectedPackageId={setPackageId}
              packageDocuments={packageDocs}
              loadingPackageDocuments={loadingPackageDocs}
              documentTypes={documentTypes}
              selectedDocumentType={selectedDocumentType}
              showUnboundDocs={showUnboundDocs}
              countsAvailable={countsAvailable}
              packageCountError={packageCountError}
              unboundDocumentCount={unboundDocumentCount}
              importingSamples={importingSamples}
              onOpenPackage={openKnowledgePackage}
              onOpenUnbound={openUnboundDocuments}
              onClosePackage={closeKnowledgePackage}
              onSelectDocumentType={selectPackageDocumentType}
              onImportSamples={importSampleKnowledge}
              onReload={loadKnowledgePackages}
            />
          )}

          {activeTab === 'approved-cards' && (
            <ApprovedKnowledgeCardsPanel
              loading={loadingApprovedCards}
              cards={approvedCards}
              summary={approvedCardSummary}
              onReload={loadApprovedKnowledgeCards}
            />
          )}

          {activeTab === 'import' && (
            <ImportTab
              uploadFile={uploadFile}
              setUploadFile={setUploadFile}
              documentType={documentType}
              setDocumentType={setDocumentType}
              projectType={projectType}
              setProjectType={setProjectType}
              packageId={packageId}
              setPackageId={setPackageId}
              packages={packages}
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

          {activeTab === 'drafts' && (
            <AssetDraftsTab
              mode={assetDraftMode}
              setMode={setAssetDraftMode}
              sourcePath={assetDraftSourcePath}
              setSourcePath={setAssetDraftSourcePath}
              observationId={assetDraftObservationId}
              setObservationId={setAssetDraftObservationId}
              observationRoot={assetDraftObservationRoot}
              setObservationRoot={setAssetDraftObservationRoot}
              directoryPath={assetDraftDirectoryPath}
              setDirectoryPath={setAssetDraftDirectoryPath}
              generating={generatingAssetDraft}
              draft={assetDraft}
              directoryResult={assetDraftDirectoryResult}
              onGenerate={handleGenerateAssetDraft}
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
              packageId={searchPackageId}
              setPackageId={setSearchPackageId}
              projectType={searchProjectType}
              setProjectType={setSearchProjectType}
              packages={packages}
            />
          )}

          {activeTab === 'samples' && (
            <SamplesTab
              samples={sampleDocs}
              loading={loadingSamples}
              importingSamples={importingSamples}
              onReload={loadSampleDocuments}
              onImportSamples={importSampleKnowledge}
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

function LegacyPackagesTab({
  packages,
  loading,
  selectedPackageId,
  setSelectedPackageId,
  packageDocuments,
  loadingPackageDocuments,
  documentTypes,
  selectedDocumentType,
  showUnboundDocs,
  countsAvailable,
  packageCountError,
  unboundDocumentCount,
  importingSamples,
  onOpenPackage,
  onOpenUnbound,
  onClosePackage,
  onSelectDocumentType,
  onImportSamples,
  onReload
}: {
  packages: KnowledgePackage[];
  loading: boolean;
  selectedPackageId: string;
  setSelectedPackageId: (value: string) => void;
  packageDocuments: SampleDocument[];
  loadingPackageDocuments: boolean;
  documentTypes: DocumentTypeStat[];
  selectedDocumentType: string;
  showUnboundDocs: boolean;
  countsAvailable: boolean;
  packageCountError: string;
  unboundDocumentCount: number;
  importingSamples: boolean;
  onOpenPackage: (packageId: string) => void;
  onOpenUnbound: () => void;
  onClosePackage: () => void;
  onSelectDocumentType: (documentType: string) => void;
  onImportSamples: () => void;
  onReload: () => void;
}) {
  const [showOnlyNonEmpty, setShowOnlyNonEmpty] = useState(false);
  const selectedPackage = showUnboundDocs ? undefined : packages.find((pkg) => pkg.package_id === selectedPackageId);
  const hasPackageContent = (pkg: KnowledgePackage) => (pkg.document_count || 0) > 0 || (pkg.approved_card_count || 0) > 0;
  const visiblePackages = showOnlyNonEmpty ? packages.filter(hasPackageContent) : packages;
  const nonEmptyPackageCount = packages.filter(hasPackageContent).length;
  const showingDocumentPanel = Boolean(selectedPackage || showUnboundDocs);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">知识包注册表</h2>
          <p className="text-sm text-gray-600 mt-1">按 `kp.xxx` 管理类型知识包、示范数据和 Milvus 过滤入口。</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onReload}
            disabled={loading}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:bg-gray-300"
          >
            刷新
          </button>
          <button
            onClick={onImportSamples}
            disabled={importingSamples}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300"
          >
            {importingSamples ? '导入中...' : selectedPackageId ? '导入所选示范数据' : '导入全部示范数据'}
          </button>
        </div>
      </div>

      {!countsAvailable && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
          Milvus 文档计数暂不可用，知识包角标不代表真实文档数。请先确认 localhost:19530 连接正常后刷新。
          {packageCountError && <span className="block mt-1 text-xs text-amber-700">{packageCountError}</span>}
        </div>
      )}

      <div className="bg-gray-50 rounded-lg p-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">当前操作知识包</label>
        <select
          value={selectedPackageId}
          onChange={(e) => {
            const nextPackageId = e.target.value;
            setSelectedPackageId(nextPackageId);
            if (nextPackageId) {
              onOpenPackage(nextPackageId);
            } else {
              onClosePackage();
            }
          }}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">全部知识包</option>
          {packages.map((pkg) => (
            <option key={pkg.package_id} value={pkg.package_id}>
              {pkg.package_id} - {pkg.title}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button
          type="button"
          onClick={onOpenUnbound}
          className={`text-left bg-white border rounded-lg p-4 hover:border-blue-400 hover:shadow-sm ${
            showUnboundDocs ? 'border-blue-500 ring-1 ring-blue-200' : 'border-gray-200'
          }`}
        >
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <h3 className="font-semibold text-gray-900">未绑定知识包文档</h3>
              <p className="text-xs text-gray-500">package_id 为空的全库文档</p>
            </div>
            <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
              {countsAvailable ? `${unboundDocumentCount} 文档` : '计数不可用'}
            </span>
          </div>
          <p className="text-xs text-gray-600">
            未选择知识包上传或历史导入的数据会出现在这里，也会参与全库文档类型统计。
          </p>
        </button>
        <div className="md:col-span-2 bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold text-gray-900">知识包覆盖情况</h3>
              <p className="text-xs text-gray-600 mt-1">
                已注册 {packages.length} 个知识包，当前有文档的知识包 {countsAvailable ? nonEmptyPackageCount : '-'} 个。
              </p>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={showOnlyNonEmpty}
                onChange={(e) => setShowOnlyNonEmpty(e.target.checked)}
              />
              仅看有文档
            </label>
          </div>
        </div>
      </div>

      {showingDocumentPanel && (
        <div className="bg-white border border-blue-200 rounded-lg p-4">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {showUnboundDocs ? '未绑定知识包文档' : selectedPackage?.title}
              </h3>
              <p className="text-xs font-mono text-gray-500">
                {showUnboundDocs ? 'package_id == ""' : selectedPackage?.package_id}
              </p>
              <p className="text-xs text-gray-600 mt-1">
                项目类型：{showUnboundDocs ? '按文档自身 project_type 统计' : selectedPackage?.project_types?.join(', ') || '-'}
              </p>
            </div>
            <button
              onClick={onClosePackage}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
            >
              返回全部知识包
            </button>
          </div>

          <div className="mb-4">
            <div className="text-sm font-medium text-gray-700 mb-2">文档类型分类</div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => onSelectDocumentType('')}
                className={`px-3 py-1.5 text-xs rounded border ${
                  !selectedDocumentType ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-300'
                }`}
              >
                全部文档
              </button>
              {documentTypes.map((item) => (
                <button
                  key={item.document_type}
                  onClick={() => onSelectDocumentType(item.document_type)}
                  className={`px-3 py-1.5 text-xs rounded border ${
                    selectedDocumentType === item.document_type
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white border-gray-300'
                  }`}
                >
                  {item.document_type} ({item.document_count})
                </button>
              ))}
              {documentTypes.length === 0 && (
                <span className="text-xs text-gray-500">当前知识包暂无文档类型数据</span>
              )}
            </div>
          </div>

          {loadingPackageDocuments ? (
            <div className="py-8 text-center text-gray-600">正在加载包内文档...</div>
          ) : packageDocuments.length > 0 ? (
            <DocumentList documents={packageDocuments} />
          ) : (
            <div className="py-8 text-center text-gray-500">当前筛选下暂无文档</div>
          )}
        </div>
      )}

      {!showingDocumentPanel && documentTypes.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">全库文档类型</h3>
          <div className="flex flex-wrap gap-2">
            {documentTypes.map((item) => (
              <span key={item.document_type} className="px-3 py-1.5 text-xs rounded bg-gray-100 text-gray-700">
                {item.document_type} ({item.document_count})
              </span>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            未绑定知识包的文档也会进入这里的文档类型统计，可在“示例文档”页签查看全库文档。
          </p>
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-gray-600">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {visiblePackages.map((pkg) => (
            <button
              key={pkg.package_id}
              type="button"
              onClick={() => onOpenPackage(pkg.package_id)}
              className={`text-left bg-white border rounded-lg p-4 hover:border-blue-400 hover:shadow-sm ${
                !showUnboundDocs && selectedPackageId === pkg.package_id ? 'border-blue-500 ring-1 ring-blue-200' : 'border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <h3 className="font-semibold text-gray-900">{pkg.title}</h3>
                  <p className="text-xs font-mono text-gray-500">{pkg.package_id}</p>
                </div>
                <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                  {countsAvailable ? `${pkg.document_count || 0} 文档` : '计数不可用'}
                </span>
              </div>
              <div className="text-xs text-gray-600 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded">
                    已审核卡 {pkg.approved_card_count || 0}
                  </span>
                  <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded">
                    激活包 {pkg.activation_pack_ref_count || 0}
                  </span>
                </div>
                {pkg.activation_pack_ids && pkg.activation_pack_ids.length > 0 && (
                  <p>关联激活包：{pkg.activation_pack_ids.join(', ')}</p>
                )}
                <p>
                  覆盖状态：{
                    pkg.coverage_status === 'ready'
                      ? '可召回'
                      : pkg.coverage_status === 'referenced_no_cards'
                        ? '已引用但缺卡'
                        : '仅注册'
                  }
                </p>
                <p>项目类型：{pkg.project_types?.join(', ') || '-'}</p>
                <div className="flex flex-wrap gap-1">
                  {(pkg.search_tags || []).slice(0, 8).map((tag) => (
                    <span key={tag} className="px-2 py-1 bg-gray-100 rounded">{tag}</span>
                  ))}
                </div>
              </div>
            </button>
          ))}
          {visiblePackages.length === 0 && (
            <div className="md:col-span-2 text-center py-8 text-gray-500">
              当前没有符合条件的知识包。可点击“导入全部示范数据”生成基础示范数据。
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AssetDraftsTab({
  mode,
  setMode,
  sourcePath,
  setSourcePath,
  observationId,
  setObservationId,
  observationRoot,
  setObservationRoot,
  directoryPath,
  setDirectoryPath,
  generating,
  draft,
  directoryResult,
  onGenerate,
}: {
  mode: AssetDraftMode;
  setMode: (mode: AssetDraftMode) => void;
  sourcePath: string;
  setSourcePath: (value: string) => void;
  observationId: string;
  setObservationId: (value: string) => void;
  observationRoot: string;
  setObservationRoot: (value: string) => void;
  directoryPath: string;
  setDirectoryPath: (value: string) => void;
  generating: boolean;
  draft: AssetDraft | null;
  directoryResult: AssetDraftDirectoryResult | null;
  onGenerate: () => void;
}) {
  const renderTextInput = (
    label: string,
    value: string,
    onChange: (value: string) => void,
    placeholder: string,
  ) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg font-mono text-sm"
      />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold">方案高参资产草稿</h2>
          <p className="text-sm text-gray-600 mt-1">
            显式读取单个文档、observation 或指定目录，生成需人工复核的 AssetDraft。
          </p>
        </div>
        <button
          type="button"
          onClick={onGenerate}
          disabled={generating}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300"
        >
          {generating ? '生成中...' : '生成草稿'}
        </button>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        草稿只做候选绑定：分类、本体维度和知识包都需要人工复核后，才允许进入资产包或上传流程。
      </div>

      <div className="bg-gray-50 rounded-lg p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">输入类型</label>
          <div className="inline-flex rounded-lg border border-gray-300 overflow-hidden bg-white">
            {[
              ['document', '单个文档'],
              ['observation', 'Observation'],
              ['directory', '指定目录'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setMode(value as AssetDraftMode)}
                className={`px-4 py-2 text-sm border-r border-gray-300 last:border-r-0 ${
                  mode === value ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {mode === 'document' && renderTextInput(
          '文档路径',
          sourcePath,
          setSourcePath,
          'D:\\path\\to\\source.md',
        )}

        {mode === 'observation' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderTextInput('Observation ID', observationId, setObservationId, 'OBS-20260608-162330-heytea')}
            {renderTextInput('Observation 根目录', observationRoot, setObservationRoot, 'D:\\path\\to\\cleaned')}
          </div>
        )}

        {mode === 'directory' && renderTextInput(
          '目录路径',
          directoryPath,
          setDirectoryPath,
          'D:\\path\\to\\selected-directory',
        )}
      </div>

      {draft && <AssetDraftPreview draft={draft} />}
      {directoryResult && <AssetDraftDirectoryPreview result={directoryResult} />}
    </div>
  );
}

function PillList({ items, tone = 'gray' }: { items?: string[]; tone?: 'gray' | 'blue' | 'green' | 'red' | 'amber' }) {
  const palette = {
    gray: 'bg-gray-100 text-gray-700',
    blue: 'bg-blue-100 text-blue-700',
    green: 'bg-green-100 text-green-700',
    red: 'bg-red-100 text-red-700',
    amber: 'bg-amber-100 text-amber-800',
  }[tone];
  const values = (items || []).filter(Boolean);
  if (values.length === 0) {
    return <span className="text-xs text-gray-500">-</span>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {values.map((item) => (
        <span key={item} className={`px-2 py-1 text-xs rounded ${palette}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function AssetDraftPreview({ draft }: { draft: AssetDraft }) {
  return (
    <div className="bg-white border border-blue-200 rounded-lg p-5 space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-mono text-gray-500">{draft.draft_id}</div>
          <h3 className="text-lg font-semibold text-gray-900 mt-1">{draft.asset_card_candidate.title}</h3>
          <p className="text-sm text-gray-600 mt-2">{draft.asset_card_candidate.summary}</p>
        </div>
        <span className="px-3 py-1 text-xs rounded bg-amber-100 text-amber-800">
          {draft.review_status}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-gray-900 mb-2">分类候选</div>
          <div className="space-y-2 text-sm text-gray-700">
            <div>项目类型：<span className="font-mono">{draft.classification_candidate?.project_type || '-'}</span></div>
            <div>子域：<span className="font-mono">{draft.classification_candidate?.subdomain_id || '-'}</span></div>
            <div>激活包：<span className="font-mono">{draft.classification_candidate?.activation_pack_id || '-'}</span></div>
            <div>置信度：{draft.classification_candidate?.confidence ?? '-'}</div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-gray-900 mb-2">本体绑定候选</div>
          <PillList items={draft.ontology_binding_candidate?.ontology_dimension_ids} tone="blue" />
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-gray-900 mb-2">知识包候选</div>
          <PillList items={draft.knowledge_binding_candidate?.package_ids} tone="green" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div className="text-sm font-semibold text-gray-900 mb-2">证据链</div>
          <div className="space-y-2 text-xs text-gray-700">
            <div>证据强度：{draft.evidence_map_candidate?.evidence_strength || '-'}</div>
            <div>来源 observation：<PillList items={draft.evidence_map_candidate?.source_observations} /></div>
            <div>清洗报告：<PillList items={draft.evidence_map_candidate?.cleaning_reports} tone="amber" /></div>
          </div>
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-900 mb-2">治理限制</div>
          <div className="space-y-3">
            <PillList items={draft.risk_flags} tone="red" />
            <div>
              <div className="text-xs text-gray-500 mb-1">不可用于</div>
              <PillList items={draft.knowledge_binding_candidate?.not_allowed_use} tone="amber" />
            </div>
          </div>
        </div>
      </div>

      <details className="bg-gray-50 rounded-lg p-4">
        <summary className="cursor-pointer text-sm font-semibold text-gray-900">查看草稿正文</summary>
        <pre className="mt-3 whitespace-pre-wrap text-xs text-gray-700 max-h-80 overflow-auto">
          {draft.asset_card_candidate.body_markdown}
        </pre>
      </details>
    </div>
  );
}

function AssetDraftDirectoryPreview({ result }: { result: AssetDraftDirectoryResult }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs text-gray-500">总项</div>
          <div className="text-xl font-bold text-gray-900">{result.total_items}</div>
        </div>
        <div className="bg-green-50 rounded-lg p-3">
          <div className="text-xs text-green-700">已生成</div>
          <div className="text-xl font-bold text-green-700">{result.generated_count}</div>
        </div>
        <div className="bg-amber-50 rounded-lg p-3">
          <div className="text-xs text-amber-700">跳过</div>
          <div className="text-xl font-bold text-amber-700">{result.skipped_count}</div>
        </div>
        <div className="bg-red-50 rounded-lg p-3">
          <div className="text-xs text-red-700">失败</div>
          <div className="text-xl font-bold text-red-700">{result.failed_count}</div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-600">
              <th className="py-2 pr-4">来源</th>
              <th className="py-2 pr-4">状态</th>
              <th className="py-2 pr-4">草稿 ID</th>
              <th className="py-2 pr-4">说明</th>
            </tr>
          </thead>
          <tbody>
            {result.items.map((item) => (
              <tr key={item.source_path} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-mono text-xs text-gray-700">{item.source_path}</td>
                <td className="py-2 pr-4">{item.status}</td>
                <td className="py-2 pr-4 font-mono text-xs">{item.draft_id || '-'}</td>
                <td className="py-2 pr-4 text-gray-600">{item.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
  packageId,
  setPackageId,
  packages,
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
                    ⏳ 正在检查上传条件...
                  </p>
                )}
                {quotaCheck && (
                  <div className="text-xs space-y-1">
                    {quotaCheck.allowed ? (
                      <div className="text-green-600">
                        ✅ 上传条件检查通过
                        {quotaCheck.quota_status && (
                          <span className="ml-2">
                            ({quotaCheck.quota_status.usage_percentage.documents.toFixed(1)}% 使用中)
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="text-red-600">
                        ❌ 上传条件不满足，无法上传
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
              <option value="类型知识">类型知识</option>
              <option value="方法论">方法论</option>
              <option value="规范知识">规范知识</option>
              <option value="运营知识">运营知识</option>
              <option value="空间策略">空间策略</option>
              <option value="治理策略">治理策略</option>
              <option value="商业策略">商业策略</option>
              <option value="教育策略">教育策略</option>
              <option value="展陈策略">展陈策略</option>
              <option value="改造策略">改造策略</option>
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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              知识包 (可选)
            </label>
            <select
              value={packageId}
              onChange={(e) => setPackageId(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">不绑定知识包</option>
              {packages.map((pkg: KnowledgePackage) => (
                <option key={pkg.package_id} value={pkg.package_id}>
                  {pkg.package_id} - {pkg.title}
                </option>
              ))}
            </select>
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
            {uploading ? '上传中...' : (quotaCheck && !quotaCheck.allowed ? '条件不满足' : '开始上传')}
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
              placeholder={`[\n  {\n    "package_id": "kp.hospitality.homestay",\n    "title": "文档标题",\n    "content": "文档内容",\n    "document_type": "设计规范",\n    "tags": ["homestay", "hospitality"],\n    "project_type": "commercial_hospitality"\n  }\n]`}
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

function DocumentList({ documents }: { documents: SampleDocument[] }) {
  return (
    <div className="space-y-3">
      {documents.map((doc, index) => (
        <div key={`${doc.source_file}-${doc.title}-${index}`} className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className="font-semibold text-gray-900">{doc.title}</h4>
              <p className="text-sm text-gray-700 mt-2 line-clamp-3">{doc.content}</p>
            </div>
            {doc.package_id && (
              <span className="shrink-0 px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                {doc.package_id}
              </span>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
            <span className="px-2 py-1 bg-gray-100 rounded">{doc.document_type || '未分类'}</span>
            {doc.project_type && <span className="px-2 py-1 bg-gray-100 rounded">{doc.project_type}</span>}
            {normalizeTags(doc.tags).map((tag, tagIndex) => (
              <span key={`${tag}-${tagIndex}`} className="px-2 py-1 bg-gray-100 rounded">{tag}</span>
            ))}
            {doc.source_file && <span className="px-2 py-1 bg-gray-100 rounded">来源: {doc.source_file}</span>}
          </div>
        </div>
      ))}
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
  setTeamId,         // 🆕 v7.141.2
  packageId,
  setPackageId,
  projectType,
  setProjectType,
  packages
}: any) {
  const selectedPackage = packages.find((pkg: KnowledgePackage) => pkg.package_id === packageId);
  const mismatchedHomestayFilter = searchQuery.includes('民宿') && packageId && packageId !== 'kp.hospitality.homestay';

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
              placeholder="试试：民宿 公区 客房 边界 / 居住 收纳 隐私 / 公共文化 展线 无障碍"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              {[
                {
                  label: '民宿边界',
                  query: '民宿 公区 客房 边界',
                  packageId: 'kp.hospitality.homestay',
                  projectType: 'commercial_hospitality',
                },
                {
                  label: '居住收纳',
                  query: '居住 收纳 隐私 生活节奏',
                  packageId: 'kp.residential',
                  projectType: 'personal_residential',
                },
                {
                  label: '展陈动线',
                  query: '公共文化 展线 无障碍 人流',
                  packageId: 'kp.public_cultural',
                  projectType: 'public_cultural',
                },
              ].map((demo) => (
                <button
                  key={demo.label}
                  type="button"
                  onClick={() => {
                    setSearchQuery(demo.query);
                    setPackageId(demo.packageId);
                    setProjectType(demo.projectType);
                  }}
                  className="px-3 py-1.5 text-xs rounded bg-white border border-blue-200 text-blue-700 hover:bg-blue-50"
                >
                  {demo.label}
                </button>
              ))}
              <button
                type="button"
                onClick={() => {
                  setPackageId('');
                  setProjectType('');
                }}
                className="px-3 py-1.5 text-xs rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                清空筛选
              </button>
            </div>
          </div>

          {(selectedPackage || projectType || mismatchedHomestayFilter) && (
            <div className={`rounded-lg border p-3 text-sm ${
              mismatchedHomestayFilter
                ? 'bg-amber-50 border-amber-200 text-amber-800'
                : 'bg-blue-50 border-blue-200 text-blue-800'
            }`}>
              当前搜索过滤：
              {selectedPackage ? ` ${selectedPackage.package_id} - ${selectedPackage.title}` : ' 全部知识包'}
              {projectType ? `；项目类型 ${projectType}` : ''}
              {mismatchedHomestayFilter ? '。查询“民宿”时建议选择 kp.hospitality.homestay 或清空筛选。' : ''}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                知识包过滤
              </label>
              <select
                value={packageId}
                onChange={(e) => setPackageId(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">全部知识包</option>
                {packages.map((pkg: KnowledgePackage) => (
                  <option key={pkg.package_id} value={pkg.package_id}>
                    {pkg.package_id} - {pkg.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                项目类型过滤
              </label>
              <input
                type="text"
                value={projectType}
                onChange={(e) => setProjectType(e.target.value)}
                placeholder="如: commercial_hospitality"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              />
            </div>
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
                  {result.metadata.package_id && (
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">{result.metadata.package_id}</span>
                  )}
                  {normalizeTags(result.metadata.tags).map((tag, i) => (
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

function SamplesTab({ samples, loading, importingSamples, onReload, onImportSamples }: {
  samples: SampleDocument[];
  loading: boolean;
  importingSamples: boolean;
  onReload: () => void;
  onImportSamples: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">📄 示例文档</h2>
        <div className="flex gap-2">
          <button
            onClick={onImportSamples}
            disabled={importingSamples}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {importingSamples ? '生成中...' : '生成基础示例数据'}
          </button>
          <button
            onClick={onReload}
            disabled={loading}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:bg-gray-400"
          >
            🔄 刷新
          </button>
        </div>
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
                {doc.package_id && (
                  <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">{doc.package_id}</span>
                )}
                {normalizeTags(doc.tags).map((tag, i) => (
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
