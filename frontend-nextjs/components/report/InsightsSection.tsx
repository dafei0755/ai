// components/report/InsightsSection.tsx
// 🔥 Phase 1.4+ 报告重构：需求洞察区块（LLM综合）
// 注意：这是LLM对所有专家报告的二次综合洞察
// 需求分析师的原始输出见 RequirementsAnalysisSection 组件

import React from 'react';
import { Lightbulb, Network, Target } from 'lucide-react';
import { InsightsSection as InsightsSectionType } from '@/types';

interface InsightsSectionProps {
  insights: InsightsSectionType | null | undefined;
}

export default function InsightsSection({ insights }: InsightsSectionProps) {
  if (!insights) {
    return null;
  }

  return (
    <div id="insights" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
      {/* 标题 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center">
          <Lightbulb className="w-5 h-5 text-cyan-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white">需求洞察（综合）</h2>
          <p className="text-sm text-gray-400 mt-1">从所有专家分析中提炼的关键发现</p>
        </div>
      </div>

      <div className="space-y-6">
        {/* 核心洞察 */}
        {insights.key_insights && insights.key_insights.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-cyan-400" />
              <h3 className="text-base font-semibold text-white">核心洞察</h3>
            </div>
            <div className="space-y-2">
              {insights.key_insights.map((insight, index) => (
                <div
                  key={index}
                  className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-sm flex items-center justify-center font-semibold">
                      {index + 1}
                    </span>
                    <p className="text-gray-200 leading-relaxed flex-1">{insight}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 跨领域关联 */}
        {insights.cross_domain_connections && insights.cross_domain_connections.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Network className="w-4 h-4 text-purple-400" />
              <h3 className="text-base font-semibold text-white">跨领域关联</h3>
            </div>
            <div className="space-y-2">
              {insights.cross_domain_connections.map((connection, index) => (
                <div
                  key={index}
                  className="bg-gradient-to-r from-purple-500/5 to-cyan-500/5 border border-purple-500/20 rounded-lg p-4"
                >
                  <p className="text-gray-200 leading-relaxed">{connection}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 用户需求深层解读 */}
        {insights.user_needs_interpretation && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-green-400" />
              <h3 className="text-base font-semibold text-white">用户需求深层解读</h3>
            </div>
            <div className="bg-gradient-to-r from-green-500/5 to-blue-500/5 border border-green-500/20 rounded-lg p-5">
              <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">
                {insights.user_needs_interpretation}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
