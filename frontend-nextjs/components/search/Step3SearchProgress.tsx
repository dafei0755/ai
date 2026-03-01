'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  CheckCircle,
  Loader2,
  Lightbulb,
  Plus,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  TrendingUp,
  FileText,
} from 'lucide-react';

/**
 * Step 3: 智能搜索执行与动态增补
 *
 * 功能：
 * - 显示搜索任务执行进度
 * - 实时展示动态增补查询
 * - 显示框架增补建议
 * - 搜索结果统计
 *
 * @version 1.0
 */

// 搜索查询状态
interface SearchQueryState {
  id: string;
  query: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'searching' | 'completed' | 'failed';
  sourcesCount: number;
  executionTime: number;
  isSupplementary?: boolean; // 是否为动态增补查询
  triggerReason?: string; // 增补触发原因
}

// 框架增补建议
interface FrameworkAddition {
  blockId: string;
  blockTitle: string;
  reason: string;
  priority: 'high' | 'medium' | 'low';
}

// 搜索结果分析
interface SearchResultAnalysis {
  totalQueries: number;
  completedQueries: number;
  totalSources: number;
  supplementaryQueries: SearchQueryState[];
  frameworkAdditions: FrameworkAddition[];
  qualityScore: number;
  coverageGaps: string[];
}

// 组件属性
interface Step3SearchProgressProps {
  sessionId: string;
  initialQueries: SearchQueryState[];
  onComplete?: (analysis: SearchResultAnalysis) => void;
  onError?: (error: string) => void;
}

export function Step3SearchProgress({
  sessionId,
  initialQueries,
  onComplete,
  onError,
}: Step3SearchProgressProps) {
  // 状态
  const [queries, setQueries] = useState<SearchQueryState[]>(initialQueries);
  const [supplementaryQueries, setSupplementaryQueries] = useState<SearchQueryState[]>([]);
  const [frameworkAdditions, setFrameworkAdditions] = useState<FrameworkAddition[]>([]);
  const [currentQuery, setCurrentQuery] = useState<string | null>(null);
  const [totalSources, setTotalSources] = useState(0);
  const [qualityScore, setQualityScore] = useState(0);
  const [coverageGaps, setCoverageGaps] = useState<string[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  // 计算进度
  const completedCount = queries.filter(q => q.status === 'completed').length;
  const totalCount = queries.length;
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  // SSE 连接
  useEffect(() => {
    const eventSource = new EventSource(
      `/api/search/four-step/stream?session_id=${sessionId}&step=3`
    );

    eventSource.addEventListener('query_start', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setCurrentQuery(data.query);
      setQueries(prev => prev.map(q =>
        q.id === data.query_id
          ? { ...q, status: 'searching' }
          : q
      ));
    });

    eventSource.addEventListener('query_complete', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setQueries(prev => prev.map(q =>
        q.id === data.query_id
          ? {
              ...q,
              status: 'completed',
              sourcesCount: data.sources_count,
              executionTime: data.execution_time,
            }
          : q
      ));
      setTotalSources(prev => prev + data.sources_count);
    });

    eventSource.addEventListener('supplementary_query', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      const newQuery: SearchQueryState = {
        id: data.query_id,
        query: data.query,
        priority: data.priority || 'medium',
        status: 'pending',
        sourcesCount: 0,
        executionTime: 0,
        isSupplementary: true,
        triggerReason: data.trigger_reason,
      };
      setSupplementaryQueries(prev => [...prev, newQuery]);
      setQueries(prev => [...prev, newQuery]);
    });

    eventSource.addEventListener('framework_addition', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      const addition: FrameworkAddition = {
        blockId: data.block_id,
        blockTitle: data.block_title,
        reason: data.reason,
        priority: data.priority || 'medium',
      };
      setFrameworkAdditions(prev => [...prev, addition]);
    });

    eventSource.addEventListener('quality_update', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setQualityScore(data.quality_score);
      setCoverageGaps(data.coverage_gaps || []);
    });

    eventSource.addEventListener('step3_complete', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setIsComplete(true);
      onComplete?.({
        totalQueries: data.total_queries,
        completedQueries: data.completed_queries,
        totalSources: data.total_sources,
        supplementaryQueries,
        frameworkAdditions,
        qualityScore: data.quality_score,
        coverageGaps: data.coverage_gaps || [],
      });
    });

    eventSource.onerror = () => {
      setError('连接失败，请刷新页面重试');
      onError?.('连接失败');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId, onComplete, onError, supplementaryQueries, frameworkAdditions]);

  // 优先级颜色
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-500/10';
      case 'medium': return 'text-yellow-600 bg-yellow-500/10';
      case 'low': return 'text-blue-600 bg-blue-500/10';
      default: return 'text-gray-600 bg-gray-500/10';
    }
  };

  // 质量分数颜色
  const getQualityColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
      {/* 头部 */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <motion.div
            animate={{
              rotate: !isComplete ? 360 : 0,
            }}
            transition={{
              duration: 2,
              repeat: !isComplete ? Infinity : 0,
              ease: 'linear',
            }}
          >
            {isComplete ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <Search className="w-5 h-5 text-purple-500" />
            )}
          </motion.div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-[var(--foreground)]">
                Step 3: 智能搜索执行
              </span>
              {!isComplete && (
                <span className="text-sm text-[var(--foreground-secondary)]">
                  {completedCount} / {totalCount} 完成
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-[var(--foreground-secondary)] mt-1">
              <span>来源: {totalSources}</span>
              {supplementaryQueries.length > 0 && (
                <span className="text-purple-600">
                  动态增补: {supplementaryQueries.length}
                </span>
              )}
              {qualityScore > 0 && (
                <span className={getQualityColor(qualityScore)}>
                  质量: {(qualityScore * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* 进度条 */}
          <div className="w-32 h-2 bg-[var(--background)] rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-purple-500"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-[var(--foreground-secondary)]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[var(--foreground-secondary)]" />
          )}
        </div>
      </div>

      {/* 展开内容 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="border-t border-[var(--border)] p-4 space-y-4">
              {/* 当前执行查询 */}
              {currentQuery && !isComplete && (
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm text-blue-600">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>正在搜索: {currentQuery}</span>
                  </div>
                </div>
              )}

              {/* 搜索查询列表 */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {queries.map((query) => (
                  <motion.div
                    key={query.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`
                      flex items-start gap-3 p-3 rounded-lg border
                      ${query.status === 'completed' ? 'bg-green-500/5 border-green-500/20' :
                        query.status === 'searching' ? 'bg-blue-500/5 border-blue-500/20' :
                        query.status === 'failed' ? 'bg-red-500/5 border-red-500/20' :
                        'bg-[var(--background)] border-[var(--border)]'}
                      ${query.isSupplementary ? 'border-l-4 border-l-purple-500' : ''}
                    `}
                  >
                    {/* 状态图标 */}
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center">
                      {query.status === 'completed' ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : query.status === 'searching' ? (
                        <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                      ) : query.status === 'failed' ? (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                      ) : (
                        <Search className="w-4 h-4 text-gray-400" />
                      )}
                    </div>

                    {/* 查询内容 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-[var(--foreground)]">
                          {query.query}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${getPriorityColor(query.priority)}`}>
                          {query.priority}
                        </span>
                        {query.isSupplementary && (
                          <span className="text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-600 flex items-center gap-1">
                            <Plus className="w-3 h-3" />
                            动态增补
                          </span>
                        )}
                      </div>
                      {query.triggerReason && (
                        <div className="text-xs text-[var(--foreground-secondary)] mb-1 flex items-center gap-1">
                          <Lightbulb className="w-3 h-3 text-purple-500" />
                          {query.triggerReason}
                        </div>
                      )}
                      {query.status === 'completed' && (
                        <div className="flex items-center gap-3 text-xs text-[var(--foreground-secondary)]">
                          <span>来源: {query.sourcesCount}</span>
                          <span>耗时: {query.executionTime.toFixed(1)}s</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* 框架增补建议 */}
              {frameworkAdditions.length > 0 && (
                <div className="bg-[var(--background)] rounded-lg p-3">
                  <h4 className="text-sm font-medium text-[var(--foreground)] mb-2 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-orange-500" />
                    框架增补建议
                  </h4>
                  <div className="space-y-2">
                    {frameworkAdditions.map((addition, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 p-2 bg-orange-500/5 border border-orange-500/20 rounded"
                      >
                        <Plus className="w-4 h-4 text-orange-500 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-[var(--foreground)]">
                            {addition.blockTitle}
                          </div>
                          <div className="text-xs text-[var(--foreground-secondary)] mt-1">
                            {addition.reason}
                          </div>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded ${getPriorityColor(addition.priority)}`}>
                          {addition.priority}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 覆盖缺口 */}
              {coverageGaps.length > 0 && (
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                  <h4 className="text-sm font-medium text-yellow-600 mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    信息覆盖缺口
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {coverageGaps.map((gap, idx) => (
                      <span
                        key={idx}
                        className="text-xs px-2 py-1 bg-yellow-500/10 text-yellow-600 rounded"
                      >
                        {gap}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 错误信息 */}
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-600 text-sm">
                  {error}
                </div>
              )}

              {/* 完成统计 */}
              {isComplete && (
                <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm text-green-600 mb-2">
                    <CheckCircle className="w-4 h-4" />
                    <span className="font-medium">搜索完成</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div>
                      <div className="text-[var(--foreground-secondary)]">总查询数</div>
                      <div className="text-lg font-semibold text-[var(--foreground)] mt-1">
                        {totalCount}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--foreground-secondary)]">总来源数</div>
                      <div className="text-lg font-semibold text-[var(--foreground)] mt-1">
                        {totalSources}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--foreground-secondary)]">质量评分</div>
                      <div className={`text-lg font-semibold mt-1 ${getQualityColor(qualityScore)}`}>
                        {(qualityScore * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default Step3SearchProgress;
