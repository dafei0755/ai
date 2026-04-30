'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  Share2,
  Sparkles,
  AlertTriangle,
  Lightbulb,
  Target,
  TrendingUp,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

/**
 * Step 4: 最终报告生成与展示
 *
 * 功能：
 * - 显示动态生成的最终报告
 * - 支持多板块内容展示
 * - 实施建议和质量标准
 * - 导出和分享功能
 *
 * @version 1.0
 */

// 文档板块
interface DocumentBlock {
  blockId: string;
  blockTitle: string;
  blockDescription: string;
  content: string;
  subItems?: {
    title: string;
    content: string;
  }[];
  qualityScore?: number;
  sourceCount?: number;
}

// 实施建议
interface ImplementationAdvice {
  category: 'priority' | 'caution' | 'optimization';
  title: string;
  description: string;
  actionItems: string[];
}

// 最终输出文档
interface FinalOutputDocument {
  coreObjective: string;
  deliverableType: string;
  blocks: DocumentBlock[];
  implementationAdvice: ImplementationAdvice[];
  qualityStandards: string[];
  overallQualityScore: number;
  totalSources: number;
  executionTime: number;
  metadata: {
    generatedAt: string;
    sessionId: string;
    queryOriginal: string;
  };
}

// 组件属性
interface Step4FinalReportProps {
  document: FinalOutputDocument;
  onExport?: (format: 'markdown' | 'pdf' | 'json') => void;
  onShare?: () => void;
}

export function Step4FinalReport({
  document,
  onExport,
  onShare,
}: Step4FinalReportProps) {
  // 状态
  const [expandedBlocks, setExpandedBlocks] = useState<Set<string>>(
    new Set(document.blocks.map(b => b.blockId))
  );
  const [showAdvice, setShowAdvice] = useState(true);
  const [showStandards, setShowStandards] = useState(false);
  const [copiedBlock, setCopiedBlock] = useState<string | null>(null);

  // 切换板块展开状态
  const toggleBlock = (blockId: string) => {
    setExpandedBlocks(prev => {
      const next = new Set(prev);
      if (next.has(blockId)) {
        next.delete(blockId);
      } else {
        next.add(blockId);
      }
      return next;
    });
  };

  // 复制板块内容
  const copyBlock = async (block: DocumentBlock) => {
    const content = `# ${block.blockTitle}\n\n${block.blockDescription}\n\n${block.content}`;
    await navigator.clipboard.writeText(content);
    setCopiedBlock(block.blockId);
    setTimeout(() => setCopiedBlock(null), 2000);
  };

  // 质量分数颜色
  const getQualityColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-500/10';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-500/10';
    return 'text-red-600 bg-red-500/10';
  };

  // 建议类别配置
  const adviceConfig = {
    priority: {
      icon: Target,
      label: '优先事项',
      color: 'text-blue-600 bg-blue-500/10 border-blue-500/20',
    },
    caution: {
      icon: AlertTriangle,
      label: '注意事项',
      color: 'text-orange-600 bg-orange-500/10 border-orange-500/20',
    },
    optimization: {
      icon: TrendingUp,
      label: '优化建议',
      color: 'text-purple-600 bg-purple-500/10 border-purple-500/20',
    },
  };

  return (
    <div className="space-y-4">
      {/* 报告头部 */}
      <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-[var(--foreground)] flex items-center gap-2">
                {document.deliverableType}
                <CheckCircle className="w-5 h-5 text-green-500" />
              </h2>
              <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                {document.coreObjective}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onExport?.('markdown')}
              className="p-2 hover:bg-[var(--surface-hover)] rounded-lg transition-colors"
              title="导出为 Markdown"
            >
              <Download className="w-4 h-4 text-[var(--foreground-secondary)]" />
            </button>
            <button
              onClick={onShare}
              className="p-2 hover:bg-[var(--surface-hover)] rounded-lg transition-colors"
              title="分享报告"
            >
              <Share2 className="w-4 h-4 text-[var(--foreground-secondary)]" />
            </button>
          </div>
        </div>

        {/* 统计信息 */}
        <div className="grid grid-cols-4 gap-4 p-4 bg-[var(--background)] rounded-lg">
          <div>
            <div className="text-xs text-[var(--foreground-secondary)]">整体质量</div>
            <div className={`text-2xl font-bold mt-1 ${getQualityColor(document.overallQualityScore).split(' ')[0]}`}>
              {(document.overallQualityScore * 100).toFixed(0)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-[var(--foreground-secondary)]">内容板块</div>
            <div className="text-2xl font-bold text-[var(--foreground)] mt-1">
              {document.blocks.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-[var(--foreground-secondary)]">参考来源</div>
            <div className="text-2xl font-bold text-[var(--foreground)] mt-1">
              {document.totalSources}
            </div>
          </div>
          <div>
            <div className="text-xs text-[var(--foreground-secondary)]">生成耗时</div>
            <div className="text-2xl font-bold text-[var(--foreground)] mt-1">
              {document.executionTime.toFixed(1)}s
            </div>
          </div>
        </div>
      </div>

      {/* 实施建议 */}
      {document.implementationAdvice.length > 0 && (
        <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors"
            onClick={() => setShowAdvice(!showAdvice)}
          >
            <div className="flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-500" />
              <span className="font-medium text-[var(--foreground)]">
                实施建议 ({document.implementationAdvice.length})
              </span>
            </div>
            {showAdvice ? (
              <ChevronUp className="w-4 h-4 text-[var(--foreground-secondary)]" />
            ) : (
              <ChevronDown className="w-4 h-4 text-[var(--foreground-secondary)]" />
            )}
          </div>
          <AnimatePresence>
            {showAdvice && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="border-t border-[var(--border)] p-4 space-y-3">
                  {document.implementationAdvice.map((advice, idx) => {
                    const config = adviceConfig[advice.category];
                    const Icon = config.icon;
                    return (
                      <div
                        key={idx}
                        className={`p-4 rounded-lg border ${config.color}`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Icon className="w-4 h-4" />
                          <span className="font-medium text-sm">{config.label}</span>
                        </div>
                        <h4 className="font-medium text-[var(--foreground)] mb-2">
                          {advice.title}
                        </h4>
                        <p className="text-sm text-[var(--foreground-secondary)] mb-3">
                          {advice.description}
                        </p>
                        {advice.actionItems.length > 0 && (
                          <ul className="space-y-1">
                            {advice.actionItems.map((item, i) => (
                              <li key={i} className="text-sm text-[var(--foreground)] flex items-start gap-2">
                                <span className="text-[var(--foreground-secondary)] mt-1">•</span>
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* 内容板块 */}
      <div className="space-y-3">
        {document.blocks.map((block, idx) => {
          const isExpanded = expandedBlocks.has(block.blockId);
          return (
            <motion.div
              key={block.blockId}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden"
            >
              {/* 板块头部 */}
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors"
                onClick={() => toggleBlock(block.blockId)}
              >
                <div className="flex items-center gap-3 flex-1">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-sm">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-[var(--foreground)]">
                      {block.blockTitle}
                    </h3>
                    <p className="text-xs text-[var(--foreground-secondary)] mt-0.5">
                      {block.blockDescription}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {block.qualityScore !== undefined && (
                    <span className={`text-xs px-2 py-1 rounded ${getQualityColor(block.qualityScore)}`}>
                      {(block.qualityScore * 100).toFixed(0)}%
                    </span>
                  )}
                  {block.sourceCount !== undefined && (
                    <span className="text-xs text-[var(--foreground-secondary)]">
                      {block.sourceCount} 来源
                    </span>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      copyBlock(block);
                    }}
                    className="p-1.5 hover:bg-[var(--background)] rounded transition-colors"
                    title="复制板块内容"
                  >
                    {copiedBlock === block.blockId ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4 text-[var(--foreground-secondary)]" />
                    )}
                  </button>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-[var(--foreground-secondary)]" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-[var(--foreground-secondary)]" />
                  )}
                </div>
              </div>

              {/* 板块内容 */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="border-t border-[var(--border)] p-6">
                      {/* 主要内容 */}
                      <div className="prose prose-sm max-w-none text-[var(--foreground)]">
                        <ReactMarkdown>{block.content}</ReactMarkdown>
                      </div>

                      {/* 子项目 */}
                      {block.subItems && block.subItems.length > 0 && (
                        <div className="mt-6 space-y-4">
                          {block.subItems.map((subItem, subIdx) => (
                            <div
                              key={subIdx}
                              className="p-4 bg-[var(--background)] rounded-lg border border-[var(--border)]"
                            >
                              <h4 className="font-medium text-[var(--foreground)] mb-2 flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-purple-500" />
                                {subItem.title}
                              </h4>
                              <div className="prose prose-sm max-w-none text-[var(--foreground-secondary)]">
                                <ReactMarkdown>{subItem.content}</ReactMarkdown>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>

      {/* 质量标准 */}
      {document.qualityStandards.length > 0 && (
        <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors"
            onClick={() => setShowStandards(!showStandards)}
          >
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="font-medium text-[var(--foreground)]">
                质量标准 ({document.qualityStandards.length})
              </span>
            </div>
            {showStandards ? (
              <ChevronUp className="w-4 h-4 text-[var(--foreground-secondary)]" />
            ) : (
              <ChevronDown className="w-4 h-4 text-[var(--foreground-secondary)]" />
            )}
          </div>
          <AnimatePresence>
            {showStandards && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="border-t border-[var(--border)] p-4">
                  <ul className="space-y-2">
                    {document.qualityStandards.map((standard, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm text-[var(--foreground)]"
                      >
                        <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                        <span>{standard}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* 元数据 */}
      <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4">
        <div className="text-xs text-[var(--foreground-secondary)] space-y-1">
          <div>会话 ID: {document.metadata.sessionId}</div>
          <div>生成时间: {new Date(document.metadata.generatedAt).toLocaleString('zh-CN')}</div>
          <div>原始查询: {document.metadata.queryOriginal}</div>
        </div>
      </div>
    </div>
  );
}

export default Step4FinalReport;
