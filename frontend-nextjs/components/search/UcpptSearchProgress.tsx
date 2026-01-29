'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Search,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Target,
  Lightbulb,
  BookOpen,
  TrendingUp,
  Zap,
} from 'lucide-react';

/**
 * ucppt 深度搜索进度面板
 *
 * 展示 ucppt 风格的多轮迭代搜索进度：
 * - 知识框架构建
 * - 迭代搜索轮次（最多30轮）
 * - 反思评估
 * - 深度钻取
 * - 整合输出
 *
 * @version 7.180
 */

// 搜索阶段类型
type SearchPhase = 'idle' | 'framework_building' | 'iterative_search' | 'deep_drilling' | 'synthesis' | 'done' | 'error';

// 轮次状态
interface RoundState {
  round: number;
  topic: string;
  query: string;
  status: 'pending' | 'searching' | 'reflecting' | 'completed';
  sourcesCount: number;
  newConcepts: string[];
  confidence: number;
  confidenceDelta: number;
  executionTime: number;
  shouldContinue?: boolean;
  gaps?: string[];
  reasoning?: string;
}

// 知识框架
interface KnowledgeFramework {
  coreConcepts: string[];
  dimensions: string[];
  initialGaps: string[];
}

// 组件属性
interface UcpptSearchProgressProps {
  query: string;
  maxRounds?: number;
  confidenceThreshold?: number;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
  autoStart?: boolean;
}

// 阶段显示配置
const phaseConfig: Record<SearchPhase, { icon: typeof Brain; label: string; color: string }> = {
  idle: { icon: Brain, label: '准备中', color: 'text-gray-400' },
  framework_building: { icon: Target, label: '框架构建', color: 'text-blue-500' },
  iterative_search: { icon: Search, label: '迭代搜索', color: 'text-purple-500' },
  deep_drilling: { icon: Zap, label: '深度钻取', color: 'text-orange-500' },
  synthesis: { icon: Lightbulb, label: '整合输出', color: 'text-green-500' },
  done: { icon: CheckCircle, label: '完成', color: 'text-green-600' },
  error: { icon: AlertCircle, label: '错误', color: 'text-red-500' },
};

export function UcpptSearchProgress({
  query,
  maxRounds = 30,
  confidenceThreshold = 0.8,
  onComplete,
  onError,
  autoStart = true,
}: UcpptSearchProgressProps) {
  // 状态
  const [phase, setPhase] = useState<SearchPhase>('idle');
  const [framework, setFramework] = useState<KnowledgeFramework | null>(null);
  const [rounds, setRounds] = useState<RoundState[]>([]);
  const [currentRound, setCurrentRound] = useState(0);
  const [confidence, setConfidence] = useState(0);
  const [totalSources, setTotalSources] = useState(0);
  const [executionTime, setExecutionTime] = useState(0);
  const [answer, setAnswer] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // EventSource 引用
  const eventSourceRef = useRef<EventSource | null>(null);
  const answerRef = useRef<HTMLDivElement>(null);

  // 启动搜索
  const startSearch = async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setPhase('idle');
    setFramework(null);
    setRounds([]);
    setCurrentRound(0);
    setConfidence(0);
    setTotalSources(0);
    setExecutionTime(0);
    setAnswer('');
    setError(null);

    try {
      // 使用 fetch + ReadableStream 处理 SSE（Next.js 兼容）
      const response = await fetch('/api/search/ucppt/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          max_rounds: maxRounds,
          confidence_threshold: confidenceThreshold,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法获取响应流');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE 事件
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        let eventData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            eventData = line.slice(6);

            if (eventType && eventData) {
              try {
                const data = JSON.parse(eventData);
                handleEvent(eventType, data);
              } catch (e) {
                console.error('解析事件数据失败:', e);
              }
              eventType = '';
              eventData = '';
            }
          }
        }
      }
    } catch (err) {
      console.error('ucppt 搜索失败:', err);
      setError(err instanceof Error ? err.message : '搜索失败');
      setPhase('error');
      onError?.(err instanceof Error ? err.message : '搜索失败');
    }
  };

  // 处理事件
  const handleEvent = (type: string, data: any) => {
    switch (type) {
      case 'phase':
        setPhase(data.phase as SearchPhase);
        break;

      case 'framework':
        setFramework({
          coreConcepts: data.core_concepts || [],
          dimensions: data.dimensions || [],
          initialGaps: data.initial_gaps || [],
        });
        break;

      case 'round_start':
        setCurrentRound(data.round);
        setConfidence(data.confidence || 0);
        setRounds(prev => {
          const newRound: RoundState = {
            round: data.round,
            topic: data.topic,
            query: data.query,
            status: 'searching',
            sourcesCount: 0,
            newConcepts: [],
            confidence: data.confidence || 0,
            confidenceDelta: 0,
            executionTime: 0,
          };
          return [...prev, newRound];
        });
        break;

      case 'round_sources':
        setRounds(prev => {
          const updated = [...prev];
          const idx = updated.findIndex(r => r.round === data.round);
          if (idx >= 0) {
            updated[idx] = {
              ...updated[idx],
              sourcesCount: data.sources_count,
              newConcepts: data.new_concepts || [],
            };
          }
          return updated;
        });
        setTotalSources(prev => prev + (data.sources_count || 0));
        break;

      case 'round_reflecting':
        setRounds(prev => {
          const updated = [...prev];
          const idx = updated.findIndex(r => r.round === data.round);
          if (idx >= 0) {
            updated[idx] = { ...updated[idx], status: 'reflecting' };
          }
          return updated;
        });
        break;

      case 'round_complete':
        setConfidence(data.confidence || 0);
        setRounds(prev => {
          const updated = [...prev];
          const idx = updated.findIndex(r => r.round === data.round);
          if (idx >= 0) {
            updated[idx] = {
              ...updated[idx],
              status: 'completed',
              confidence: data.confidence || 0,
              confidenceDelta: data.confidence_delta || 0,
              executionTime: data.execution_time || 0,
              shouldContinue: data.should_continue,
              gaps: data.gaps || [],
              reasoning: data.reasoning,
            };
          }
          return updated;
        });
        break;

      case 'search_complete':
        // 搜索阶段完成
        break;

      case 'drill_start':
        setPhase('deep_drilling');
        setCurrentRound(data.round);
        break;

      case 'drill_complete':
        setTotalSources(prev => prev + (data.sources_count || 0));
        break;

      case 'answer_chunk':
        setAnswer(prev => prev + (data.content || ''));
        // 自动滚动到底部
        if (answerRef.current) {
          answerRef.current.scrollTop = answerRef.current.scrollHeight;
        }
        break;

      case 'done':
        setPhase('done');
        setExecutionTime(data.execution_time || 0);
        setTotalSources(data.total_sources || 0);
        setConfidence(data.final_confidence || 0);
        onComplete?.({
          totalRounds: data.totalRounds || data.total_rounds || 0,
          totalSources: data.total_sources,
          confidence: data.final_confidence,
          executionTime: data.execution_time,
          answer,
        });
        break;

      case 'error':
        setError(data.message);
        setPhase('error');
        onError?.(data.message);
        break;
    }
  };

  // 自动启动
  useEffect(() => {
    if (autoStart && query) {
      startSearch();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [query, autoStart]);

  // 获取阶段配置
  const currentPhaseConfig = phaseConfig[phase];
  const PhaseIcon = currentPhaseConfig.icon;

  // 置信度颜色
  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'bg-green-500';
    if (conf >= 0.6) return 'bg-yellow-500';
    if (conf >= 0.4) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
      {/* 头部 - 阶段状态 */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <motion.div
            animate={{
              rotate: phase === 'iterative_search' || phase === 'deep_drilling' ? 360 : 0,
            }}
            transition={{
              duration: 2,
              repeat: phase === 'iterative_search' || phase === 'deep_drilling' ? Infinity : 0,
              ease: 'linear',
            }}
          >
            <PhaseIcon className={`w-5 h-5 ${currentPhaseConfig.color}`} />
          </motion.div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-[var(--foreground)]">
                {currentPhaseConfig.label}
              </span>
              {phase === 'iterative_search' && (
                <span className="text-sm text-[var(--foreground-secondary)]">
                  第 {currentRound} / {maxRounds} 轮
                </span>
              )}
            </div>
            {phase !== 'idle' && phase !== 'error' && (
              <div className="flex items-center gap-3 text-xs text-[var(--foreground-secondary)] mt-1">
                <span>置信度: {(confidence * 100).toFixed(0)}%</span>
                <span>来源: {totalSources}</span>
                {executionTime > 0 && <span>耗时: {executionTime.toFixed(1)}s</span>}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* 置信度进度条 */}
          {phase !== 'idle' && phase !== 'error' && (
            <div className="w-24 h-2 bg-[var(--background)] rounded-full overflow-hidden">
              <motion.div
                className={`h-full ${getConfidenceColor(confidence)}`}
                initial={{ width: 0 }}
                animate={{ width: `${confidence * 100}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
          )}
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
              {/* 知识框架 */}
              {framework && (
                <div className="bg-[var(--background)] rounded-lg p-3">
                  <h4 className="text-sm font-medium text-[var(--foreground)] mb-2 flex items-center gap-2">
                    <Target className="w-4 h-4 text-blue-500" />
                    知识框架
                  </h4>
                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div>
                      <div className="text-[var(--foreground-secondary)] mb-1">核心概念</div>
                      <div className="flex flex-wrap gap-1">
                        {framework.coreConcepts.map((c, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-blue-500/10 text-blue-600 rounded"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--foreground-secondary)] mb-1">探索维度</div>
                      <div className="flex flex-wrap gap-1">
                        {framework.dimensions.map((d, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-purple-500/10 text-purple-600 rounded"
                          >
                            {d}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="text-[var(--foreground-secondary)] mb-1">信息缺口</div>
                      <div className="flex flex-wrap gap-1">
                        {framework.initialGaps.slice(0, 3).map((g, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-orange-500/10 text-orange-600 rounded"
                          >
                            {g}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 搜索轮次列表 */}
              {rounds.length > 0 && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {rounds.map((round) => (
                    <motion.div
                      key={round.round}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`
                        flex items-start gap-3 p-3 rounded-lg border
                        ${round.status === 'completed' ? 'bg-green-500/5 border-green-500/20' :
                          round.status === 'reflecting' ? 'bg-yellow-500/5 border-yellow-500/20' :
                          round.status === 'searching' ? 'bg-blue-500/5 border-blue-500/20' :
                          'bg-[var(--background)] border-[var(--border)]'}
                      `}
                    >
                      {/* 轮次标识 */}
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center">
                        {round.status === 'completed' ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : round.status === 'reflecting' ? (
                          <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin" />
                        ) : (
                          <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                        )}
                      </div>

                      {/* 轮次内容 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-[var(--foreground)]">
                            第 {round.round} 轮: {round.topic}
                          </span>
                          {round.status === 'completed' && (
                            <span className="text-xs text-[var(--foreground-secondary)]">
                              {round.executionTime.toFixed(1)}s
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-[var(--foreground-secondary)] truncate mt-1">
                          {round.query}
                        </div>
                        {round.status === 'completed' && (
                          <div className="flex items-center gap-4 mt-2 text-xs">
                            <span className="text-[var(--foreground-secondary)]">
                              来源: {round.sourcesCount}
                            </span>
                            <span className={round.confidenceDelta >= 0 ? 'text-green-600' : 'text-red-600'}>
                              置信度: {round.confidenceDelta >= 0 ? '+' : ''}{(round.confidenceDelta * 100).toFixed(1)}%
                            </span>
                            {round.newConcepts.length > 0 && (
                              <span className="text-purple-600">
                                新概念: {round.newConcepts.length}
                              </span>
                            )}
                          </div>
                        )}
                        {round.reasoning && (
                          <div className="text-xs text-[var(--foreground-secondary)] mt-2 italic">
                            💭 {round.reasoning}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}

              {/* 回答内容（流式） */}
              {answer && (
                <div
                  ref={answerRef}
                  className="bg-[var(--background)] rounded-lg p-4 max-h-96 overflow-y-auto"
                >
                  <h4 className="text-sm font-medium text-[var(--foreground)] mb-3 flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-green-500" />
                    深度回答
                  </h4>
                  <div className="prose prose-sm max-w-none text-[var(--foreground)]">
                    {answer}
                  </div>
                </div>
              )}

              {/* 错误信息 */}
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-600 text-sm">
                  {error}
                </div>
              )}

              {/* 操作按钮 */}
              {(phase === 'done' || phase === 'error') && (
                <div className="flex justify-end">
                  <button
                    onClick={startSearch}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    重新搜索
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default UcpptSearchProgress;
