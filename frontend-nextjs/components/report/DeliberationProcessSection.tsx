// components/report/DeliberationProcessSection.tsx
// 🔥 Phase 1.4+ 报告重构：推敲过程区块

import React from 'react';
import { Brain, Users, Target, Workflow } from 'lucide-react';
import { DeliberationProcess as DeliberationProcessType } from '@/types';

interface DeliberationProcessSectionProps {
  deliberationProcess: DeliberationProcessType | null | undefined;
}

export default function DeliberationProcessSection({ deliberationProcess }: DeliberationProcessSectionProps) {
  if (!deliberationProcess) {
    return null;
  }

  return (
    <div id="deliberation-process" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
      {/* 标题 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-violet-500/20 flex items-center justify-center">
          <Brain className="w-5 h-5 text-violet-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white">推敲过程</h2>
          <p className="text-sm text-gray-400 mt-1">项目总监的战略分析与决策思路</p>
        </div>
      </div>

      <div className="space-y-5">
        {/* 探询架构 */}
        <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-5">
          <div className="flex items-center gap-2 mb-3">
            <Workflow className="w-4 h-4 text-violet-400" />
            <h3 className="text-base font-semibold text-white">探询架构选择</h3>
          </div>
          <div className="bg-gradient-to-r from-violet-500/10 to-purple-500/10 border border-violet-500/20 rounded-lg p-4 mb-3">
            <p className="text-lg font-semibold text-violet-300">{deliberationProcess.inquiry_architecture}</p>
          </div>
          {deliberationProcess.reasoning && (
            <p className="text-gray-300 leading-relaxed">{deliberationProcess.reasoning}</p>
          )}
        </div>

        {/* 专家角色选择 */}
        {deliberationProcess.role_selection && deliberationProcess.role_selection.length > 0 && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Users className="w-4 h-4 text-blue-400" />
              <h3 className="text-base font-semibold text-white">专家角色配置</h3>
            </div>
            <div className="space-y-2">
              {deliberationProcess.role_selection.map((role, index) => (
                <div
                  key={index}
                  className="bg-gradient-to-r from-blue-500/5 to-cyan-500/5 border border-blue-500/20 rounded-lg p-3"
                >
                  <p className="text-gray-200">{role}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 战略方向 */}
        {deliberationProcess.strategic_approach && (
          <div className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-orange-400" />
              <h3 className="text-base font-semibold text-white">整体战略方向</h3>
            </div>
            <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">
              {deliberationProcess.strategic_approach}
            </p>
          </div>
        )}
      </div>

      {/* 提示信息 */}
      <div className="mt-5 text-xs text-gray-500 text-center">
        💡 此部分展示项目总监如何基于需求特性选择最适合的分析策略
      </div>
    </div>
  );
}
