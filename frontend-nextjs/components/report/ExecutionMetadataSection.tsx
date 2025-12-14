// components/report/ExecutionMetadataSection.tsx
// 🔥 Phase 1.4+ 报告重构：执行元数据汇总区块
// 🆕 v7.4: 增强元数据展示，提升用户体验

import React from 'react';
import { BarChart3, Clock, Users, Target, Award, RefreshCcw, Layers, FileQuestion, Gauge, Calendar, PieChart } from 'lucide-react';
import { ExecutionMetadata } from '@/types';

interface ExecutionMetadataSectionProps {
  metadata: ExecutionMetadata | null | undefined;
  expertReportsCount?: number;
}

export default function ExecutionMetadataSection({ metadata, expertReportsCount }: ExecutionMetadataSectionProps) {
  // 如果没有元数据，但有专家报告数量，则创建基础元数据
  const displayMetadata = {
    total_experts: metadata?.total_experts ?? expertReportsCount ?? 0,
    inquiry_architecture: metadata?.inquiry_architecture || '深度优先探询',
    analysis_duration: metadata?.analysis_duration,
    total_tokens_used: metadata?.total_tokens_used,
    confidence_average: metadata?.confidence_average,
    review_rounds: metadata?.review_rounds,
    total_batches: metadata?.total_batches,
    complexity_level: metadata?.complexity_level,
    questionnaire_answered: metadata?.questionnaire_answered,
    expert_distribution: metadata?.expert_distribution,
    generated_at: metadata?.generated_at,
  };

  if (!displayMetadata.total_experts && !displayMetadata.inquiry_architecture) {
    return null;
  }

  // 格式化生成时间
  const formatGeneratedAt = (isoString?: string) => {
    if (!isoString) return null;
    try {
      const date = new Date(isoString);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return null;
    }
  };

  // 专家分布标签映射
  const distributionLabels: Record<string, string> = {
    'V2_设计总监': '设计总监',
    'V3_领域专家': '领域专家',
    'V4_研究专家': '研究专家',
    'V5_创新专家': '创新专家',
    'V6_实施专家': '实施专家',
  };

  const generatedAt = formatGeneratedAt(displayMetadata.generated_at);

  return (
    <div id="execution-metadata" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
      {/* 标题 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-slate-500/20 flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-slate-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">执行元数据汇总</h2>
            <p className="text-sm text-gray-400 mt-1">分析过程的统计信息</p>
          </div>
        </div>
        {generatedAt && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Calendar className="w-3.5 h-3.5" />
            <span>{generatedAt}</span>
          </div>
        )}
      </div>

      {/* 主要统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-4">
        {/* 专家数量 */}
        <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-medium text-gray-400">专家数量</h3>
          </div>
          <p className="text-2xl font-bold text-white">{displayMetadata.total_experts}</p>
        </div>

        {/* 批次数量 */}
        {displayMetadata.total_batches !== undefined && displayMetadata.total_batches > 0 && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-medium text-gray-400">执行批次</h3>
            </div>
            <p className="text-2xl font-bold text-white">{displayMetadata.total_batches}</p>
          </div>
        )}

        {/* 复杂度等级 */}
        {displayMetadata.complexity_level && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Gauge className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-medium text-gray-400">复杂度</h3>
            </div>
            <p className={`text-lg font-semibold ${
              displayMetadata.complexity_level === '复杂' ? 'text-red-400' :
              displayMetadata.complexity_level === '中等' ? 'text-yellow-400' :
              'text-green-400'
            }`}>
              {displayMetadata.complexity_level}
            </p>
          </div>
        )}

        {/* 问卷回答数 */}
        {displayMetadata.questionnaire_answered !== undefined && displayMetadata.questionnaire_answered > 0 && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileQuestion className="w-4 h-4 text-teal-400" />
              <h3 className="text-xs font-medium text-gray-400">问卷回答</h3>
            </div>
            <p className="text-2xl font-bold text-white">{displayMetadata.questionnaire_answered}</p>
          </div>
        )}

        {/* 分析耗时 */}
        {displayMetadata.analysis_duration && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-green-400" />
              <h3 className="text-xs font-medium text-gray-400">分析耗时</h3>
            </div>
            <p className="text-lg font-bold text-white">{displayMetadata.analysis_duration}</p>
          </div>
        )}

        {/* 平均置信度 */}
        {displayMetadata.confidence_average !== undefined && displayMetadata.confidence_average !== null && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Award className="w-4 h-4 text-yellow-400" />
              <h3 className="text-xs font-medium text-gray-400">平均置信度</h3>
            </div>
            <p className="text-2xl font-bold text-white">
              {Math.round(displayMetadata.confidence_average * 100)}%
            </p>
          </div>
        )}

        {/* 审核轮次 */}
        {displayMetadata.review_rounds !== undefined && displayMetadata.review_rounds > 0 && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <RefreshCcw className="w-4 h-4 text-orange-400" />
              <h3 className="text-xs font-medium text-gray-400">审核轮次</h3>
            </div>
            <p className="text-2xl font-bold text-white">{displayMetadata.review_rounds}</p>
          </div>
        )}

        {/* Token使用量 */}
        {displayMetadata.total_tokens_used !== undefined && displayMetadata.total_tokens_used > 0 && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-medium text-gray-400">Token使用</h3>
            </div>
            <p className="text-lg font-bold text-white">
              {(displayMetadata.total_tokens_used / 1000).toFixed(1)}K
            </p>
          </div>
        )}
      </div>

      {/* 探询架构 - 单独一行 */}
      <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-medium text-gray-400">探询架构</h3>
        </div>
        <p className="text-base font-medium text-purple-300">
          {displayMetadata.inquiry_architecture}
        </p>
      </div>

      {/* 专家分布 - 如果有数据 */}
      {displayMetadata.expert_distribution && Object.keys(displayMetadata.expert_distribution).length > 0 && (
        <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <PieChart className="w-4 h-4 text-pink-400" />
            <h3 className="text-xs font-medium text-gray-400">专家分布</h3>
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.entries(displayMetadata.expert_distribution).map(([key, count]) => (
              <div 
                key={key} 
                className="flex items-center gap-2 bg-[var(--card-bg)] px-3 py-1.5 rounded-full"
              >
                <span className="text-sm text-gray-300">
                  {distributionLabels[key] || key}
                </span>
                <span className="text-sm font-semibold text-white bg-[var(--primary)]/20 px-2 py-0.5 rounded-full">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 提示信息 */}
      <div className="mt-5 text-xs text-gray-500 text-center">
        📊 执行元数据帮助您了解分析过程的规模和质量
      </div>
    </div>
  );
}
