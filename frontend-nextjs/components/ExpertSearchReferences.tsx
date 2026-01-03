'use client';

import { useState, useMemo } from 'react';
import { ExternalLink, Search, ChevronDown, ChevronUp, User } from 'lucide-react';

/**
 * 按专家分组的搜索引用组件 (v7.113)
 *
 * 展示每个专家使用的搜索资料，按专家分组显示
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
}

interface ExpertSearchReferencesProps {
  references: SearchReference[];
  expertReports?: Record<string, any>;
  className?: string;
}

// 搜索工具图标
const TOOL_ICONS: Record<string, string> = {
  bocha: '🔍',
  tavily: '🌐',
  arxiv: '📚',
  ragflow: '🗂️'
};

export function ExpertSearchReferences({
  references,
  expertReports = {},
  className = ''
}: ExpertSearchReferencesProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [expandedExperts, setExpandedExperts] = useState<Set<string>>(new Set());

  // 按专家分组引用
  const groupedReferences = useMemo(() => {
    const groups: Record<string, SearchReference[]> = {};

    references.forEach(ref => {
      // 从 deliverable_id 提取专家ID (格式: "2-1_1_143022_abc" -> "2-1")
      const expertId = ref.deliverable_id.split('_')[0];

      if (!groups[expertId]) {
        groups[expertId] = [];
      }
      groups[expertId].push(ref);
    });

    return groups;
  }, [references]);

  // 获取专家名称
  const getExpertName = (expertId: string): string => {
    // 尝试从expertReports中获取专家名称
    for (const [key, value] of Object.entries(expertReports)) {
      if (key.includes(expertId)) {
        // 从key中提取专家名称，格式如 "V2_设计总监_2-1"
        const parts = key.split('_');
        if (parts.length >= 2) {
          return parts[1]; // 返回 "设计总监"
        }
      }
    }

    // 降级方案：根据ID推断
    const idParts = expertId.split('-');
    if (idParts.length === 2) {
      const typeMap: Record<string, string> = {
        '2': '设计研究分析师',
        '3': '技术架构师',
        '4': '用户体验设计师',
        '5': '商业分析师',
        '6': '实施规划师'
      };
      return typeMap[idParts[0]] || `专家 ${expertId}`;
    }

    return `专家 ${expertId}`;
  };

  // 切换专家展开状态
  const toggleExpert = (expertId: string) => {
    const newExpanded = new Set(expandedExperts);
    if (newExpanded.has(expertId)) {
      newExpanded.delete(expertId);
    } else {
      newExpanded.add(expertId);
    }
    setExpandedExperts(newExpanded);
  };

  if (!references || references.length === 0) {
    return null;
  }

  const expertIds = Object.keys(groupedReferences).sort();

  return (
    <div className={`border rounded-lg bg-white shadow-sm ${className}`}>
      {/* 头部 */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors border-b"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">👥</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              专家搜索资料
            </h3>
            <p className="text-sm text-gray-500">
              {expertIds.length} 位专家 · {references.length} 条引用
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
        <div className="divide-y">
          {expertIds.map(expertId => {
            const expertRefs = groupedReferences[expertId];
            const expertName = getExpertName(expertId);
            const isExpertExpanded = expandedExperts.has(expertId);

            // 统计搜索工具使用
            const toolCounts: Record<string, number> = {};
            expertRefs.forEach(ref => {
              const tool = ref.source_tool;
              toolCounts[tool] = (toolCounts[tool] || 0) + 1;
            });

            return (
              <div key={expertId} className="p-4">
                {/* 专家头部 */}
                <div
                  className="flex items-center justify-between cursor-pointer hover:bg-gray-50 -m-2 p-2 rounded-lg transition-colors"
                  onClick={() => toggleExpert(expertId)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                      {expertId}
                    </div>
                    <div>
                      <h4 className="font-semibold text-gray-900">{expertName}</h4>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span>{expertRefs.length} 条引用</span>
                        <span>·</span>
                        <div className="flex gap-1">
                          {Object.entries(toolCounts).map(([tool, count]) => (
                            <span key={tool} title={tool}>
                              {TOOL_ICONS[tool] || '🔍'} {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <button className="p-1 hover:bg-gray-100 rounded transition-colors">
                    {isExpertExpanded ? (
                      <ChevronUp className="w-5 h-5 text-gray-600" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-600" />
                    )}
                  </button>
                </div>

                {/* 引用列表 */}
                {isExpertExpanded && (
                  <div className="mt-4 space-y-3 ml-13">
                    {expertRefs.map((ref, idx) => (
                      <ExpertReferenceCard
                        key={idx}
                        reference={ref}
                        index={idx + 1}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// 专家引用卡片（简化版）
function ExpertReferenceCard({ reference, index }: { reference: SearchReference; index: number }) {
  const toolIcon = TOOL_ICONS[reference.source_tool] || '🔍';

  return (
    <div className="border border-gray-200 rounded-lg p-3 hover:shadow-md transition-shadow bg-gray-50">
      <div className="flex items-start gap-2">
        <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">
          {index}
        </span>

        <div className="flex-1 min-w-0">
          {/* 标题 */}
          <h5 className="font-medium text-sm text-gray-900 mb-1">
            {reference.url ? (
              <a
                href={reference.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 hover:underline inline-flex items-center gap-1"
              >
                {reference.title}
                <ExternalLink className="w-3 h-3 flex-shrink-0" />
              </a>
            ) : (
              reference.title
            )}
          </h5>

          {/* 摘要 */}
          <p className="text-xs text-gray-600 mb-2 line-clamp-2">
            {reference.snippet}
          </p>

          {/* 元信息 */}
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span className="px-1.5 py-0.5 bg-white border border-gray-300 rounded">
              {toolIcon} {reference.source_tool}
            </span>

            <span className="flex items-center gap-1">
              <Search className="w-3 h-3" />
              {reference.query}
            </span>

            {reference.relevance_score !== undefined && (
              <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                {(reference.relevance_score * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
