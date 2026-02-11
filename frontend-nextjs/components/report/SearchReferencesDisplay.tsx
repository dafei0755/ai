// components/report/SearchReferencesDisplay.tsx
// 🆕 v7.113: 搜索引用展示组件
// 🆕 v7.164: 添加ID支持，优化key和去重

'use client';

import React from 'react';
import { ExternalLink, BookOpen, FileText, Database, Search, Globe } from 'lucide-react';
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
	milvus: Database,
	serper: Globe,
};

// 工具名称映射
const TOOL_NAMES = {
	tavily: 'Tavily 网络搜索',
	arxiv: 'Arxiv 学术检索',
	ragflow: 'RAGFlow 知识库',
	bocha: 'Bocha 搜索',
	milvus: 'Milvus 知识库',
	serper: 'Serper 搜索',
};

// 工具颜色映射
const TOOL_COLORS = {
	tavily: 'text-blue-600 bg-blue-50',
	arxiv: 'text-purple-600 bg-purple-50',
	ragflow: 'text-green-600 bg-green-50',
	bocha: 'text-orange-600 bg-orange-50',
	milvus: 'text-teal-600 bg-teal-50',
	serper: 'text-indigo-600 bg-indigo-50',
};

export const SearchReferencesDisplay: React.FC<SearchReferencesDisplayProps> = ({
	references,
	className = '',
}) => {
	// 🆕 v7.164: 基于ID去重 - v7.209: 移到条件返回之前
	const deduplicatedRefs = React.useMemo(() => {
		if (!references || references.length === 0) return [];
		const seen = new Set<string>();
		return references.filter(ref => {
			const key = ref.id || `${ref.source_tool}_${ref.url || ref.title}`;
			if (seen.has(key)) return false;
			seen.add(key);
			return true;
		});
	}, [references]);

	if (!references || references.length === 0) {
		return null;
	}

	// 按来源工具分组
	const groupedByTool = deduplicatedRefs.reduce((acc, ref) => {
		const tool = ref.source_tool || 'unknown';
		if (!acc[tool]) {
			acc[tool] = [];
		}
		acc[tool].push(ref);
		return acc;
	}, {} as Record<string, SearchReference[]>);

	return (
		<div className={`mt-6 border-t border-[var(--border-color)] pt-6 ${className}`}>
			<h3 className="text-lg font-semibold mb-5 flex items-center gap-2 text-[var(--foreground)]">
				<Search className="w-5 h-5 text-[var(--primary)]" />
				搜索引用
				<span className="text-sm font-normal text-[var(--foreground-secondary)]">
					({deduplicatedRefs.length} 条)
				</span>
			</h3>

			<div className="space-y-6">
				{Object.entries(groupedByTool).map(([tool, refs]) => {
					const Icon = TOOL_ICONS[tool as keyof typeof TOOL_ICONS] || FileText;
					const toolName = TOOL_NAMES[tool as keyof typeof TOOL_NAMES] || tool;
					const colorClass = TOOL_COLORS[tool as keyof typeof TOOL_COLORS] || 'text-gray-600 bg-gray-50';

					return (
						<div key={tool} className="space-y-3">
							{/* 工具标题 */}
							<div className="flex items-center gap-2 mb-3">
								<div className={`p-1.5 rounded-lg ${colorClass}`}>
									<Icon className="w-4 h-4" />
								</div>
								<h4 className="font-semibold text-sm text-[var(--foreground)]">{toolName}</h4>
								<span className="text-xs text-[var(--foreground-secondary)] bg-[var(--sidebar-bg)] px-2 py-0.5 rounded-full">
									{refs.length} 条结果
								</span>
							</div>

							{/* 引用列表 - 🔧 v7.175: 统一字体样式 */}
							<div className="space-y-2.5 ml-8">
								{refs.map((ref, idx) => (
									<div
										key={ref.id || `${ref.url}-${idx}`}
										className="group border border-[var(--border-color)] rounded-lg p-4 hover:border-[var(--primary)] hover:shadow-sm transition-all bg-[var(--card-bg)]"
									>
										{/* 标题行 */}
										<div className="flex items-start justify-between gap-2 mb-2">
											{/* 标题和链接 */}
											<a
												href={ref.url}
												target="_blank"
												rel="noopener noreferrer"
												className="font-medium text-sm leading-snug text-[var(--foreground)] hover:text-[var(--primary)] transition-colors flex items-start gap-1.5 flex-1"
											>
												<span className="flex-1 line-clamp-2">{ref.title}</span>
												<ExternalLink className="w-4 h-4 mt-0.5 flex-shrink-0 opacity-0 group-hover:opacity-60 transition-opacity" />
											</a>
											{/* ID标签 */}
											{ref.id && (
												<span className="text-[10px] text-[var(--foreground-secondary)] font-mono ml-2 flex-shrink-0 bg-[var(--sidebar-bg)] px-1.5 py-0.5 rounded">
													#{ref.id.split('_').pop()?.slice(0, 8)}
												</span>
											)}
										</div>

										{/* 摘要 - 统一字体样式 */}
										{ref.snippet && (
											<p className="text-xs leading-relaxed text-[var(--foreground-secondary)] line-clamp-2 mb-3">
												{ref.snippet}
											</p>
										)}

										{/* 元数据 - 统一颜色变量 */}
										<div className="flex flex-wrap items-center gap-3 text-xs">
											{ref.relevance_score !== undefined && (
												<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300">
													相关性: {Math.round(ref.relevance_score * 100)}%
												</span>
											)}
											{ref.quality_score !== undefined && (
												<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
													质量: {Math.round(ref.quality_score)}分
												</span>
											)}
											{ref.query && (
												<span className="text-[var(--foreground-secondary)] truncate max-w-xs" title={ref.query}>
													🔍 {ref.query}
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
