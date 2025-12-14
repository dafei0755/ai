// components/report/CoreAnswerSection.tsx
// 🔥 Phase 1.4+ P4 & v7.0: 核心答案显示组件（支持多交付物格式）
// 🎯 v7.3: 优化核心答案显示 - 直接展示专家完整输出（Markdown渲染）

'use client';

import { useState } from 'react';
import { Lightbulb, Package, Clock, DollarSign, ChevronDown, ChevronUp, Users, Award, CheckCircle, MessageSquare } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

/** 🆕 v7.0: 单个交付物的责任者答案 */
interface DeliverableAnswer {
  deliverable_id: string;
  deliverable_name: string;
  deliverable_type?: string;
  owner_role: string;
  owner_answer: string;
  answer_summary?: string;
  supporters: string[];
  quality_score?: number | null;
}

/** 🆕 v7.0: 专家支撑链 */
interface ExpertSupportChain {
  role_id: string;
  role_name: string;
  contribution_type: string;
  contribution_summary: string;
  related_deliverables: string[];
}

interface CoreAnswer {
  question: string;
  answer: string;
  deliverables: string[];
  timeline: string;
  budget_range: string;
  // v7.0 新字段
  deliverable_answers?: DeliverableAnswer[];
  expert_support_chain?: ExpertSupportChain[];
}

interface CoreAnswerSectionProps {
  coreAnswer: CoreAnswer | null | undefined;
}

// 🔥 v7.6: 使用统一的格式化函数
import { formatExpertName as getRoleDisplayName } from '@/lib/formatters';

/** 单个交付物卡片组件 */
function DeliverableCard({ deliverable, index }: { deliverable: DeliverableAnswer; index: number }) {
  const [expanded, setExpanded] = useState(index === 0); // 第一个默认展开
  
  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-xl overflow-hidden mb-4">
      {/* 卡片头部 */}
      <div 
        className="flex items-center justify-between p-5 cursor-pointer hover:bg-[var(--hover-bg)] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
            <span className="text-green-400 font-bold text-lg">{deliverable.deliverable_id || `D${index + 1}`}</span>
          </div>
          <div>
            <h4 className="text-white font-semibold text-lg">{deliverable.deliverable_name}</h4>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
                {getRoleDisplayName(deliverable.owner_role)}
              </span>
              {deliverable.quality_score && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                  完成度 {Math.round(deliverable.quality_score)}%
                </span>
              )}
              {deliverable.owner_answer && (
                <span className="text-xs text-gray-500">
                  {deliverable.owner_answer.length} 字
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {deliverable.supporters && deliverable.supporters.length > 0 && (
            <span className="text-xs text-gray-500">
              +{deliverable.supporters.length} 支撑专家
            </span>
          )}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>
      
      {/* 展开内容 */}
      {expanded && (
        <div className="border-t border-[var(--border-color)] p-6">
          {/* 🎯 核心：直接显示专家的完整输出（Markdown渲染） */}
          {deliverable.owner_answer && (
            <div className="mb-6">
              <div className="prose prose-invert prose-sm max-w-none">
                <MarkdownRenderer content={deliverable.owner_answer} />
              </div>
            </div>
          )}

          {/* 支撑专家（折叠显示） */}
          {deliverable.supporters && deliverable.supporters.length > 0 && (
            <details className="mt-6">
              <summary className="text-sm text-gray-400 cursor-pointer hover:text-gray-300 flex items-center gap-2">
                <Users className="w-4 h-4" />
                查看支撑专家 ({deliverable.supporters.length} 位)
              </summary>
              <div className="mt-3 flex flex-wrap gap-2">
                {deliverable.supporters.map((supporter, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-3 py-1.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/30"
                  >
                    {getRoleDisplayName(supporter)}
                  </span>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

/** 专家支撑链组件 */
function ExpertSupportChainSection({ chain }: { chain: ExpertSupportChain[] }) {
  const [expanded, setExpanded] = useState(false);
  
  if (!chain || chain.length === 0) return null;
  
  return (
    <div className="mt-6 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-xl overflow-hidden">
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-[var(--hover-bg)] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <Award className="w-5 h-5 text-purple-400" />
          <span className="text-white font-medium">专家支撑链</span>
          <span className="text-xs text-gray-500">({chain.length} 位支撑专家)</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </div>
      
      {expanded && (
        <div className="border-t border-[var(--border-color)] p-4 space-y-3">
          {chain.map((expert, idx) => (
            <div key={idx} className="flex items-start gap-3 p-3 bg-[var(--sidebar-bg)] rounded-lg">
              <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-purple-400 text-sm font-medium">{idx + 1}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-white font-medium">{getRoleDisplayName(expert.role_id)}</span>
                  {expert.related_deliverables && expert.related_deliverables.length > 0 && (
                    <span className="text-xs text-gray-500">
                      → {expert.related_deliverables.join(', ')}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-400 line-clamp-2">{expert.contribution_summary}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CoreAnswerSection({ coreAnswer }: CoreAnswerSectionProps) {
  // 检测是否是 v7.0 格式
  const isV7Format = coreAnswer?.deliverable_answers && coreAnswer.deliverable_answers.length > 0;

  // 如果没有任何内容，不渲染
  if (!coreAnswer || (!coreAnswer.answer && !isV7Format)) {
    return null;
  }

  return (
    <div id="core-answer" className="bg-gradient-to-r from-green-500/10 to-cyan-500/10 border border-green-500/30 rounded-2xl p-8">
      {/* 标题区域 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
          <Lightbulb className="w-6 h-6 text-green-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">核心答案</h2>
          <p className="text-sm text-gray-400 mt-1">
            {isV7Format
              ? '各责任专家对您问题的直接回答'
              : '基于多专家分析的核心建议'
            }
          </p>
        </div>
      </div>

      {/* 核心问题 */}
      {coreAnswer.question && (
        <div className="mb-6 bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            您的核心问题
          </h3>
          <p className="text-gray-200 text-xl leading-relaxed font-medium">{coreAnswer.question}</p>
        </div>
      )}

      {/* v7.0 格式：多交付物答案 */}
      {isV7Format && coreAnswer.deliverable_answers && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
            <Package className="w-4 h-4" />
            各交付物责任者答案
          </h3>
          {coreAnswer.deliverable_answers.map((da, idx) => (
            <DeliverableCard key={da.deliverable_id || idx} deliverable={da} index={idx} />
          ))}
        </div>
      )}

      {/* 旧格式：单一核心答案 */}
      {!isV7Format && coreAnswer.answer && (
        <div className="mb-6 bg-gradient-to-r from-green-500/5 to-cyan-500/5 border-l-4 border-green-500 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-green-400 mb-3">我们的建议</h3>
          <p className="text-white text-xl font-medium leading-relaxed">
            {coreAnswer.answer}
          </p>
        </div>
      )}

      {/* 专家支撑链 (v7.0) */}
      {isV7Format && coreAnswer.expert_support_chain && (
        <ExpertSupportChainSection chain={coreAnswer.expert_support_chain} />
      )}

      {/* 提示信息 */}
      <div className="mt-6 text-xs text-gray-500 text-center">
        {isV7Format
          ? '💡 以上为各专家对您问题的完整答案，更多背景研究和实施细节请查看下方"专家原始报告"区块'
          : '💡 以上是基于当前信息的初步建议，详细分析请参考下方章节'
        }
      </div>
    </div>
  );
}
