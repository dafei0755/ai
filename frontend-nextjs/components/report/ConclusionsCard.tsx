// components/report/ConclusionsCard.tsx
// 结论卡片组件

'use client';

import { FC } from 'react';
import { Target, ArrowRight, CheckSquare } from 'lucide-react';
import { Conclusions } from '@/types';

interface ConclusionsCardProps {
  conclusions: Conclusions;
}

const ConclusionsCard: FC<ConclusionsCardProps> = ({ conclusions }) => {
  const hasContent = (
    conclusions.project_analysis_summary ||
    (conclusions.next_steps && conclusions.next_steps.length > 0) ||
    (conclusions.success_metrics && conclusions.success_metrics.length > 0)
  );

  if (!hasContent) return null;

  return (
    <div className="bg-gradient-to-br from-green-900/30 to-teal-900/30 border border-green-500/30 rounded-2xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
          <Target className="w-5 h-5 text-green-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">结论与建议</h2>
      </div>

      {/* 项目分析总结 */}
      {conclusions.project_analysis_summary && (
        <div className="bg-[var(--sidebar-bg)]/50 rounded-lg p-4 border border-[var(--border-color)]">
          <h3 className="text-sm font-medium text-gray-400 mb-2">项目分析总结</h3>
          <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
            {conclusions.project_analysis_summary}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 下一步行动 */}
        {conclusions.next_steps && conclusions.next_steps.length > 0 && (
          <div className="bg-[var(--sidebar-bg)]/50 rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <ArrowRight className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-medium text-gray-400">下一步行动</h3>
            </div>
            <ul className="space-y-2">
              {conclusions.next_steps.map((step, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                    {index + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 成功指标 */}
        {conclusions.success_metrics && conclusions.success_metrics.length > 0 && (
          <div className="bg-[var(--sidebar-bg)]/50 rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <CheckSquare className="w-4 h-4 text-green-400" />
              <h3 className="text-sm font-medium text-gray-400">成功指标</h3>
            </div>
            <ul className="space-y-2">
              {conclusions.success_metrics.map((metric, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-green-400 mt-1 flex-shrink-0">✓</span>
                  <span>{metric}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConclusionsCard;
