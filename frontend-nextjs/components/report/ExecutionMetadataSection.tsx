// components/report/ExecutionMetadataSection.tsx
// 🔥 Phase 1.4+ 报告重构：执行元数据汇总区块

import React from 'react';
import { BarChart3, Clock, Users, Target, Award, RefreshCcw } from 'lucide-react';
import { ExecutionMetadata } from '@/types';

interface ExecutionMetadataSectionProps {
  metadata: ExecutionMetadata | null | undefined;
  expertReportsCount?: number;
}

export default function ExecutionMetadataSection({ metadata, expertReportsCount }: ExecutionMetadataSectionProps) {
  // 如果没有元数据，但有专家报告数量，则创建基础元数据
  const displayMetadata = metadata || {
    total_experts: expertReportsCount || 0,
    inquiry_architecture: '未知',
  };

  if (!displayMetadata.total_experts && !displayMetadata.inquiry_architecture) {
    return null;
  }

  return (
    <div id="execution-metadata" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
      {/* 标题 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-slate-500/20 flex items-center justify-center">
          <BarChart3 className="w-5 h-5 text-slate-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white">执行元数据汇总</h2>
          <p className="text-sm text-gray-400 mt-1">分析过程的统计信息</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* 专家数量 */}
        <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-medium text-gray-400">专家数量</h3>
          </div>
          <p className="text-2xl font-bold text-white">{displayMetadata.total_experts}</p>
        </div>

        {/* 探询架构 */}
        <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4 col-span-2">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-purple-400" />
            <h3 className="text-xs font-medium text-gray-400">探询架构</h3>
          </div>
          <p className="text-lg font-semibold text-purple-300 truncate" title={displayMetadata.inquiry_architecture}>
            {displayMetadata.inquiry_architecture}
          </p>
        </div>

        {/* 分析耗时 */}
        {displayMetadata.analysis_duration && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-green-400" />
              <h3 className="text-xs font-medium text-gray-400">分析耗时</h3>
            </div>
            <p className="text-2xl font-bold text-white">{displayMetadata.analysis_duration}</p>
          </div>
        )}

        {/* 平均置信度 */}
        {displayMetadata.confidence_average !== undefined && (
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

      {/* 提示信息 */}
      <div className="mt-5 text-xs text-gray-500 text-center">
        📊 执行元数据帮助您了解分析过程的规模和质量
      </div>
    </div>
  );
}
