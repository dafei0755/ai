'use client';

import { useState, useMemo } from 'react';
import { ExternalLink, Search, ChevronDown, ChevronUp, Filter } from 'lucide-react';

/**
 * 搜索引用组件 (v7.113)
 *
 * 展示专家分析过程中使用的搜索资料和参考文献
 */

interface SearchReference {
  source_tool: string;
  title: string;
  url?: string;
  snippet: string;
  relevance_score?: number;
  deliverable_id: string;
  query: string;
  timestamp: string;
  llm_relevance_score?: number;
  llm_scoring_reason?: string;
}

interface SearchReferencesProps {
  references: SearchReference[];
  className?: string;
}

// 搜索工具图标映射
const TOOL_ICONS: Record<string, string> = {
  bocha: '🔍',
  tavily: '🌐',
  arxiv: '📚',
  ragflow: '🗂️'
};

// 搜索工具名称映射
const TOOL_NAMES: Record<string, string> = {
  bocha: '博查搜索',
  tavily: 'Tavily搜索',
  arxiv: 'arXiv学术',
  ragflow: 'RAGFlow知识库'
};

export function SearchReferences({ references, className = '' }: SearchReferencesProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [selectedTool, setSelectedTool] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 计算搜索工具统计
  const toolStats = useMemo(() => {
    const stats: Record<string, number> = {};
    references.forEach(ref => {
      const tool = ref.source_tool || 'unknown';
      stats[tool] = (stats[tool] || 0) + 1;
    });
    return stats;
  }, [references]);

  // 过滤引用
  const filteredReferences = useMemo(() => {
    let filtered = references;

    // 按工具过滤
    if (selectedTool !== 'all') {
      filtered = filtered.filter(ref => ref.source_tool === selectedTool);
    }

    // 按搜索关键词过滤
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(ref =>
        ref.title.toLowerCase().includes(query) ||
        ref.snippet.toLowerCase().includes(query) ||
        ref.query.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [references, selectedTool, searchQuery]);

  if (!references || references.length === 0) {
    return null;
  }

  return (
    <div className={`border rounded-lg bg-white shadow-sm ${className}`}>
      {/* 头部 */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors border-b"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">📚</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              参考文献
            </h3>
            <p className="text-sm text-gray-500">
              专家分析使用的搜索资料 · {references.length} 条引用
            </p>
          </div>
        </div>
        <button className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-600" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-600" />
          )}
        </button>
      </div>

      {/* 内容区 */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* 工具栏 */}
          <div className="flex flex-col sm:flex-row gap-3">
            {/* 搜索框 */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索标题、摘要或查询..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* 工具筛选 */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={selectedTool}
                onChange={(e) => setSelectedTool(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">所有来源 ({references.length})</option>
                {Object.entries(toolStats).map(([tool, count]) => (
                  <option key={tool} value={tool}>
                    {TOOL_ICONS[tool] || '🔍'} {TOOL_NAMES[tool] || tool} ({count})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* 引用列表 */}
          <div className="space-y-3">
            {filteredReferences.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Search className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p>未找到匹配的引用</p>
              </div>
            ) : (
              filteredReferences.map((ref, idx) => (
                <ReferenceCard key={idx} reference={ref} index={idx + 1} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// 单个引用卡片
function ReferenceCard({ reference, index }: { reference: SearchReference; index: number }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const toolIcon = TOOL_ICONS[reference.source_tool] || '🔍';
  const toolName = TOOL_NAMES[reference.source_tool] || reference.source_tool;

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-gray-50">
      {/* 头部信息 */}
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-blue-100 text-blue-700 rounded-full text-sm font-semibold">
          {index}
        </span>

        <div className="flex-1 min-w-0">
          {/* 标题和链接 */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <h4 className="font-medium text-gray-900 flex-1">
              {reference.url ? (
                <a
                  href={reference.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-blue-600 hover:underline inline-flex items-center gap-1"
                >
                  {reference.title}
                  <ExternalLink className="w-4 h-4 flex-shrink-0" />
                </a>
              ) : (
                reference.title
              )}
            </h4>

            {/* 来源标签 */}
            <span className="flex-shrink-0 px-2 py-1 bg-white border border-gray-300 rounded text-xs text-gray-600">
              {toolIcon} {toolName}
            </span>
          </div>

          {/* 摘要 */}
          <p className="text-sm text-gray-600 mb-2 line-clamp-2">
            {reference.snippet}
          </p>

          {/* 元信息 */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Search className="w-3 h-3" />
              查询: {reference.query}
            </span>

            {reference.relevance_score !== undefined && (
              <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded">
                相关性: {(reference.relevance_score * 100).toFixed(0)}%
              </span>
            )}

            {reference.deliverable_id && (
              <span className="text-gray-400">
                交付物: {reference.deliverable_id.split('_')[0]}
              </span>
            )}
          </div>

          {/* 展开/收起详情 */}
          {(reference.llm_relevance_score || reference.llm_scoring_reason) && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="mt-2 text-xs text-blue-600 hover:text-blue-700 hover:underline"
            >
              {isExpanded ? '收起详情' : '查看详情'}
            </button>
          )}

          {/* 详细信息 */}
          {isExpanded && (
            <div className="mt-3 p-3 bg-white rounded border border-gray-200 text-sm space-y-2">
              {reference.llm_relevance_score !== undefined && (
                <div>
                  <span className="font-medium text-gray-700">LLM评分: </span>
                  <span className="text-gray-600">
                    {(reference.llm_relevance_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}

              {reference.llm_scoring_reason && (
                <div>
                  <span className="font-medium text-gray-700">评分理由: </span>
                  <span className="text-gray-600">{reference.llm_scoring_reason}</span>
                </div>
              )}

              {reference.url && (
                <div>
                  <span className="font-medium text-gray-700">URL: </span>
                  <a
                    href={reference.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline break-all"
                  >
                    {reference.url}
                  </a>
                </div>
              )}

              <div>
                <span className="font-medium text-gray-700">时间: </span>
                <span className="text-gray-600">
                  {new Date(reference.timestamp).toLocaleString('zh-CN')}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
