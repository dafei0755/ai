// components/report/SearchReferencesDisplay.tsx
// 🆕 v7.113: 搜索引用展示组件

'use client';

import React from 'react';
import { ExternalLink, BookOpen, FileText, Database, Search } from 'lucide-react';
import type { SearchReference } from '@/types';

interface SearchReferencesDisplayProps {
	references: SearchReference[];
	className?: string;
}

// 工具图标映射
const TOOL_ICONS = {
	tavily: Search,
	arxiv: BookOpen,
	ragflow: Database,
	bocha: FileText,
};

// 工具名称映射
const TOOL_NAMES = {
	tavily: 'Tavily 网络搜索',
	arxiv: 'Arxiv 学术检索',
	ragflow: 'RAGFlow 知识库',
	bocha: 'Bocha 搜索',
};

// 工具颜色映射
const TOOL_COLORS = {
	tavily: 'text-blue-600 bg-blue-50',
	arxiv: 'text-purple-600 bg-purple-50',
	ragflow: 'text-green-600 bg-green-50',
	bocha: 'text-orange-600 bg-orange-50',
};

export const SearchReferencesDisplay: React.FC<SearchReferencesDisplayProps> = ({
	references,
	className = '',
}) => {
	if (!references || references.length === 0) {
		return null;
	}

	// 按来源工具分组
	const groupedByTool = references.reduce((acc, ref) => {
		const tool = ref.source_tool || 'unknown';
		if (!acc[tool]) {
			acc[tool] = [];
		}
		acc[tool].push(ref);
		return acc;
	}, {} as Record<string, SearchReference[]>);

	return (
		<div className={`mt-6 border-t pt-6 ${className}`}>
			<h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
				<Search className="w-5 h-5" />
				搜索引用
				<span className="text-sm font-normal text-gray-500">
					({references.length} 条)
				</span>
			</h3>

			<div className="space-y-6">
				{Object.entries(groupedByTool).map(([tool, refs]) => {
					const Icon = TOOL_ICONS[tool as keyof typeof TOOL_ICONS] || FileText;
					const toolName = TOOL_NAMES[tool as keyof typeof TOOL_NAMES] || tool;
					const colorClass = TOOL_COLORS[tool as keyof typeof TOOL_COLORS] || 'text-gray-600 bg-gray-50';

					return (
						<div key={tool} className="space-y-2">
							{/* 工具标题 */}
							<div className="flex items-center gap-2 mb-3">
								<div className={`p-1.5 rounded ${colorClass}`}>
									<Icon className="w-4 h-4" />
								</div>
								<h4 className="font-medium text-sm">{toolName}</h4>
								<span className="text-xs text-gray-500">
									{refs.length} 条结果
								</span>
							</div>

							{/* 引用列表 */}
							<div className="space-y-2 ml-8">
								{refs.map((ref, idx) => (
									<div
										key={`${ref.url}-${idx}`}
										className="border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
									>
										{/* 标题和链接 */}
										<a
											href={ref.url}
											target="_blank"
											rel="noopener noreferrer"
											className="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-start gap-1 mb-2"
										>
											<span className="flex-1">{ref.title}</span>
											<ExternalLink className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
										</a>

										{/* 摘要 */}
										{ref.snippet && (
											<p className="text-xs text-gray-600 line-clamp-2 mb-2">
												{ref.snippet}
											</p>
										)}

										{/* 元数据 */}
										<div className="flex items-center gap-3 text-xs text-gray-500">
											{ref.relevance_score !== undefined && (
												<span>
													相关性: {Math.round(ref.relevance_score * 100)}%
												</span>
											)}
											{ref.quality_score !== undefined && (
												<span>
													质量: {Math.round(ref.quality_score)}分
												</span>
											)}
											{ref.query && (
												<span className="truncate max-w-xs" title={ref.query}>
													查询: {ref.query}
												</span>
											)}
										</div>
									</div>
								))}
							</div>
						</div>
					);
				})}
			</div>
		</div>
	);
};

export default SearchReferencesDisplay;
