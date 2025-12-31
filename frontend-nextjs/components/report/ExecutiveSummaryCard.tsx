// components/report/ExecutiveSummaryCard.tsx
// 执行摘要卡片组件

'use client';

import { FC } from 'react';
import { FileText, Lightbulb, CheckCircle, Star } from 'lucide-react';
import { ExecutiveSummary } from '@/types';

interface ExecutiveSummaryCardProps {
  summary: ExecutiveSummary;
}

const ExecutiveSummaryCard: FC<ExecutiveSummaryCardProps> = ({ summary }) => {
  return (
    <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 border border-blue-500/30 rounded-2xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
          <FileText className="w-5 h-5 text-blue-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">执行摘要</h2>
      </div>

      {/* 项目概述 */}
      {summary.project_overview && (
        <div className="bg-[var(--sidebar-bg)]/50 rounded-lg p-4 border border-[var(--border-color)]">
          <h3 className="text-sm font-medium text-gray-400 mb-2">项目概述</h3>
          <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
            {summary.project_overview}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 关键发现 */}
        {summary.key_findings && summary.key_findings.length > 0 && (
          <div className="bg-[var(--sidebar-bg)]/50 rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="w-4 h-4 text-yellow-400" />
              <h3 className="text-sm font-medium text-gray-400">关键发现</h3>
            </div>
            <ul className="space-y-2">
              {summary.key_findings.map((finding, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-yellow-400 mt-1">•</span>
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 核心建议 */}
        {summary.key_recommendations && summary.key_recommendations.length > 0 && (
          <div className="bg-[var(--sidebar-bg)]/50 rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <h3 className="text-sm font-medium text-gray-400">核心建议</h3>
            </div>
            <ul className="space-y-2">
              {summary.key_recommendations.map((rec, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-green-400 mt-1">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 成功要素 */}
        {summary.success_factors && summary.success_factors.length > 0 && (
          <div className="bg-[var(--sidebar-bg)]/50 rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <Star className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-medium text-gray-400">成功要素</h3>
            </div>
            <ul className="space-y-2">
              {summary.success_factors.map((factor, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-purple-400 mt-1">•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExecutiveSummaryCard;
