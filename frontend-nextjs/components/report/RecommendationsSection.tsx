// components/report/RecommendationsSection.tsx
// 🔥 Phase 1.4+ 报告重构：建议提醒区块（V2升级 - 五维度分类）

'use client';

import React from 'react';
import {
  CheckCircle,
  Target,        // 🎯 重点
  Flame,         // 🔥 难点
  Eye,           // 👁️ 易忽略
  AlertTriangle, // ⚠️ 有风险
  Sparkles       // ✨ 理想
} from 'lucide-react';
import { RecommendationsSection as RecommendationsSectionType, RecommendationItem } from '@/types';

interface RecommendationsSectionProps {
  recommendations: RecommendationsSectionType | null | undefined;
}

// 维度配置
const DIMENSION_CONFIG = {
  critical: {
    title: '🎯 重点',
    subtitle: '项目核心工作，必须完成',
    icon: Target,
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/30',
    textColor: 'text-red-400',
    badgeColor: 'bg-red-500/20 text-red-400'
  },
  difficult: {
    title: '🔥 难点',
    subtitle: '技术难度高，需要重点攻克',
    icon: Flame,
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500/30',
    textColor: 'text-orange-400',
    badgeColor: 'bg-orange-500/20 text-orange-400'
  },
  overlooked: {
    title: '👁️ 易忽略',
    subtitle: '容易被遗漏但很重要',
    icon: Eye,
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    textColor: 'text-blue-400',
    badgeColor: 'bg-blue-500/20 text-blue-400'
  },
  risky: {
    title: '⚠️ 有风险',
    subtitle: '不做会出问题',
    icon: AlertTriangle,
    bgColor: 'bg-amber-500/20',
    borderColor: 'border-amber-500/30',
    textColor: 'text-amber-400',
    badgeColor: 'bg-amber-500/20 text-amber-400'
  },
  ideal: {
    title: '✨ 理想',
    subtitle: '锦上添花，有余力再做',
    icon: Sparkles,
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/30',
    textColor: 'text-purple-400',
    badgeColor: 'bg-purple-500/20 text-purple-400'
  }
} as const;

// 辅助函数：格式化专家名称
function formatExpertName(expertId: string): string {
  // V2_设计总监_2-2 → 设计总监
  const parts = expertId.split('_');
  return parts.length >= 2 ? parts[1] : expertId;
}

export default function RecommendationsSection({ recommendations }: RecommendationsSectionProps) {
  if (!recommendations || !recommendations.recommendations || recommendations.recommendations.length === 0) {
    return null;
  }

  // 按维度分组
  const groupedRecommendations = recommendations.recommendations.reduce((acc, item) => {
    if (!acc[item.dimension]) {
      acc[item.dimension] = [];
    }
    acc[item.dimension].push(item);
    return acc;
  }, {} as Record<string, RecommendationItem[]>);

  // 维度顺序
  const dimensionOrder: Array<keyof typeof DIMENSION_CONFIG> = [
    'critical',
    'difficult',
    'overlooked',
    'risky',
    'ideal'
  ];

  return (
    <div id="recommendations" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
      {/* 标题 */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
          <CheckCircle className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white">建议提醒</h2>
          <p className="text-sm text-gray-400 mt-1">{recommendations.summary}</p>
        </div>
      </div>

      {/* 建议列表 */}
      <div className="space-y-5">
        {dimensionOrder.map(dimension => {
          const items = groupedRecommendations[dimension];
          if (!items || items.length === 0) return null;

          const config = DIMENSION_CONFIG[dimension];
          const Icon = config.icon;

          return (
            <div key={dimension} className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-5">
              {/* 维度标题 */}
              <div className="flex items-center gap-2 mb-4">
                <div className={`w-8 h-8 rounded-full ${config.bgColor} flex items-center justify-center`}>
                  <Icon className={`w-4 h-4 ${config.textColor}`} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">{config.title}</h3>
                  <p className="text-xs text-gray-400">{config.subtitle}</p>
                </div>
              </div>

              {/* 建议列表 */}
              <ul className="space-y-3">
                {items.map((item, index) => (
                  <li key={index} className={`border ${config.borderColor} rounded-lg p-3`}>
                    {/* 建议内容 */}
                    <div className="flex items-start gap-3">
                      <span className={`flex-shrink-0 w-6 h-6 rounded-full ${config.badgeColor} text-xs flex items-center justify-center font-semibold mt-0.5`}>
                        {index + 1}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm text-gray-200 leading-relaxed">{item.content}</p>

                        {/* 元信息 */}
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-400">
                          {/* 理由 */}
                          <div className="flex items-center gap-1">
                            <span className="text-gray-500">💡</span>
                            <span>{item.reasoning}</span>
                          </div>

                          {/* 工作量 */}
                          {item.estimated_effort && (
                            <div className="flex items-center gap-1">
                              <span className="text-gray-500">⏱️</span>
                              <span>{item.estimated_effort}</span>
                            </div>
                          )}

                          {/* 来源专家 */}
                          <div className="flex items-center gap-1">
                            <span className="text-gray-500">👤</span>
                            <span>{formatExpertName(item.source_expert)}</span>
                          </div>

                          {/* 依赖 */}
                          {item.dependencies && item.dependencies.length > 0 && (
                            <div className="flex items-center gap-1">
                              <span className="text-gray-500">🔗</span>
                              <span>依赖 {item.dependencies.length} 项</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* 提示信息 */}
      <div className="mt-6 bg-gradient-to-r from-green-500/5 to-blue-500/5 border border-green-500/20 rounded-lg p-4">
        <p className="text-xs text-gray-400 text-center">
          💡 建议按"重点-难点-易忽略-有风险-理想"五个维度组织，帮助您全面把控项目
        </p>
      </div>
    </div>
  );
}
