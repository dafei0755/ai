// components/report/ComprehensiveAnalysisCard.tsx
// 综合分析卡片组件

'use client';

import { FC } from 'react';
import { Brain, TrendingUp, AlertTriangle, Map } from 'lucide-react';
import { ComprehensiveAnalysis } from '@/types';

interface ComprehensiveAnalysisCardProps {
  analysis: ComprehensiveAnalysis;
}

const ComprehensiveAnalysisCard: FC<ComprehensiveAnalysisCardProps> = ({ analysis }) => {
  const hasContent = (
    (analysis.cross_domain_insights && analysis.cross_domain_insights.length > 0) ||
    (analysis.integrated_recommendations && analysis.integrated_recommendations.length > 0) ||
    (analysis.risk_assessment && analysis.risk_assessment.length > 0) ||
    (analysis.implementation_roadmap && analysis.implementation_roadmap.length > 0)
  );

  if (!hasContent) return null;

  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-cyan-500/20 rounded-lg flex items-center justify-center">
          <Brain className="w-5 h-5 text-cyan-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">综合分析</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 跨领域洞察 */}
        {analysis.cross_domain_insights && analysis.cross_domain_insights.length > 0 && (
          <div className="bg-[var(--sidebar-bg)] rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-medium text-gray-400">跨领域洞察</h3>
            </div>
            <ul className="space-y-2">
              {analysis.cross_domain_insights.map((insight, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-cyan-400 mt-1 flex-shrink-0">{index + 1}.</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 整合建议 */}
        {analysis.integrated_recommendations && analysis.integrated_recommendations.length > 0 && (
          <div className="bg-[var(--sidebar-bg)] rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <h3 className="text-sm font-medium text-gray-400">整合建议</h3>
            </div>
            <ul className="space-y-2">
              {analysis.integrated_recommendations.map((rec, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-green-400 mt-1 flex-shrink-0">{index + 1}.</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 风险评估 */}
        {analysis.risk_assessment && analysis.risk_assessment.length > 0 && (
          <div className="bg-[var(--sidebar-bg)] rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-medium text-gray-400">风险评估</h3>
            </div>
            <ul className="space-y-2">
              {analysis.risk_assessment.map((risk, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-amber-400 mt-1 flex-shrink-0">⚠</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 实施路线图 */}
        {analysis.implementation_roadmap && analysis.implementation_roadmap.length > 0 && (
          <div className="bg-[var(--sidebar-bg)] rounded-lg p-4 border border-[var(--border-color)]">
            <div className="flex items-center gap-2 mb-3">
              <Map className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-medium text-gray-400">实施路线图</h3>
            </div>
            <ul className="space-y-2">
              {analysis.implementation_roadmap.map((step, index) => (
                <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-purple-400 mt-1 flex-shrink-0">→</span>
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComprehensiveAnalysisCard;
