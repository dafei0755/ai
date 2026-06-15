'use client';

import { useState } from 'react';

export interface KnowledgePackage {
  package_id: string;
  title: string;
  project_types: string[];
  search_tags: string[];
  document_types: string[];
  status: string;
  document_count: number;
  approved_card_count?: number;
  approved_card_ids?: string[];
  activation_pack_ids?: string[];
  activation_pack_ref_count?: number;
  coverage_status?: string;
}

export interface DocumentTypeStat {
  document_type: string;
  document_count: number;
}

export interface SampleDocument {
  title: string;
  content: string;
  document_type: string;
  tags: string[] | string;
  project_type: string;
  source_file: string;
  package_id?: string;
  owner_type?: string;
  owner_id?: string;
  visibility?: string;
  team_id?: string;
}

export function PackagesTab({
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
  onReload,
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
            <div className="space-y-3">
              {packageDocuments.map((doc, index) => (
                <article key={`${doc.source_file}-${index}`} className="border border-gray-200 rounded p-3">
                  <h4 className="font-medium text-gray-900">{doc.title}</h4>
                  <p className="mt-1 text-xs text-gray-500">
                    {doc.document_type} · {doc.project_type || '-'} · {doc.source_file}
                  </p>
                </article>
              ))}
            </div>
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
            未绑定知识包的文档也会进入这里的文档类型统计，可在示例文档页筛查全库文档。
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

