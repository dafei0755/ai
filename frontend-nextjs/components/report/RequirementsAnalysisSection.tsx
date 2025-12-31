/**
 * 需求分析结果区块组件
 * 展示需求分析师（Requirements Analyst）的原始输出
 * 
 * 与 InsightsSection 的区别：
 * - InsightsSection: LLM对所有专家报告的二次综合洞察
 * - RequirementsAnalysisSection: 需求分析师的第一手分析结果
 * 
 * 展示的6个完整字段（融合用户修改后的最终版本）：
 * 1. project_overview - 项目概览
 * 2. core_objectives - 核心目标
 * 3. project_tasks - 项目任务
 * 4. narrative_characters - 叙事角色
 * 5. physical_contexts - 物理环境
 * 6. constraints_opportunities - 约束与机遇
 */

import React from 'react';
import { RequirementsAnalysis } from '@/types';
import {
  FileText,
  Target,
  CheckSquare,
  Users,
  MapPin,
  AlertCircle,
  Lightbulb,
} from 'lucide-react';

interface RequirementsAnalysisSectionProps {
  requirements: RequirementsAnalysis;
}

const RequirementsAnalysisSection: React.FC<RequirementsAnalysisSectionProps> = ({
  requirements,
}) => {
  // 解析约束与机遇
  const constraints = requirements.constraints_opportunities?.constraints || [];
  const opportunities = requirements.constraints_opportunities?.opportunities || [];

  return (
    <div id="requirements-analysis" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-8">
      {/* 标题区域 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
          <FileText className="w-6 h-6 text-blue-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">需求分析结果</h2>
          <p className="text-sm text-gray-400 mt-1">
            需求分析师的深度解读 · 融合您的补充信息后的最终分析
          </p>
        </div>
      </div>

      <div className="space-y-6">
          {/* 项目概览 */}
        {requirements.project_overview && (
          <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)]">
            <div className="flex items-start gap-3 mb-4">
              <FileText className="w-5 h-5 text-blue-400 mt-1 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-2">项目概览</h3>
                <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {requirements.project_overview}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 核心目标 */}
        {requirements.core_objectives && requirements.core_objectives.length > 0 && (
          <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)]">
            <div className="flex items-start gap-3 mb-4">
              <Target className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-3">核心目标</h3>
                <ul className="space-y-2">
                  {requirements.core_objectives.map((objective, index) => (
                    <li key={index} className="text-gray-300 leading-relaxed">{objective}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* 项目任务 */}
        {requirements.project_tasks && requirements.project_tasks.length > 0 && (
          <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)]">
            <div className="flex items-start gap-3 mb-4">
              <CheckSquare className="w-5 h-5 text-purple-400 mt-1 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-3">项目任务</h3>
                <ul className="space-y-2">
                  {requirements.project_tasks.map((task, index) => (
                    <li key={index} className="text-gray-300 leading-relaxed">{task}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 叙事角色 */}
          {requirements.narrative_characters && requirements.narrative_characters.length > 0 && (
            <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)]">
              <div className="flex items-start gap-3 mb-4">
                <Users className="w-5 h-5 text-indigo-400 mt-1 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-3">叙事角色</h3>
                  <ul className="space-y-2">
                    {requirements.narrative_characters.map((character, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-gray-300 text-sm leading-relaxed flex-1">
                          {character}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* 物理环境 */}
          {requirements.physical_contexts && requirements.physical_contexts.length > 0 && (
            <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)]">
              <div className="flex items-start gap-3 mb-4">
                <MapPin className="w-5 h-5 text-orange-400 mt-1 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-3">物理环境</h3>
                  <ul className="space-y-2">
                    {requirements.physical_contexts.map((context, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-gray-300 text-sm leading-relaxed flex-1">
                          {context}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 约束与机遇 */}
        {(constraints.length > 0 || opportunities.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 约束 */}
            {constraints.length > 0 && (
              <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)]">
                <div className="flex items-start gap-3 mb-4">
                  <AlertCircle className="w-5 h-5 text-red-400 mt-1 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-3">约束条件</h3>
                    <ul className="space-y-2">
                      {constraints.map((constraint: string, index: number) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-gray-300 text-sm leading-relaxed flex-1">
                            {constraint}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* 机遇 */}
            {opportunities.length > 0 && (
              <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)]">
                <div className="flex items-start gap-3 mb-4">
                  <Lightbulb className="w-5 h-5 text-yellow-400 mt-1 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-3">发展机遇</h3>
                    <ul className="space-y-2">
                      {opportunities.map((opportunity: string, index: number) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-gray-300 text-sm leading-relaxed flex-1">
                            {opportunity}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RequirementsAnalysisSection;
