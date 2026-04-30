/**
 * 解题思路/搜索清单展示卡片 - v7.290 增强
 *
 * 展示UCPPT搜索模式第一步生成的解题思路，包括：
 * - 任务本质识别
 * - 搜索清单（5-8步，含搜索关键词、成功标准、优先级）
 * - 关键突破口
 * - 预期产出形态
 * - MECE覆盖校验（v7.290 新增）
 */

import React, { useState } from 'react';
import { ProblemSolvingApproach, SolutionStep, BreakthroughPoint } from '@/types';

interface ProblemSolvingApproachCardProps {
  approach: ProblemSolvingApproach;
  className?: string;
}

export const ProblemSolvingApproachCard: React.FC<ProblemSolvingApproachCardProps> = ({
  approach,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  // 复杂度颜色映射
  const complexityColors = {
    simple: 'bg-green-100 text-green-800 border-green-300',
    moderate: 'bg-blue-100 text-blue-800 border-blue-300',
    complex: 'bg-orange-100 text-orange-800 border-orange-300',
    highly_complex: 'bg-red-100 text-red-800 border-red-300',
  };

  // 任务类型图标映射
  const taskTypeIcons = {
    research: '🔍',
    design: '🎨',
    decision: '⚖️',
    exploration: '🧭',
    verification: '✅',
  };

  // v7.290: 优先级颜色映射
  const priorityColors = {
    high: 'bg-red-100 text-red-700 border-red-300',
    medium: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    low: 'bg-gray-100 text-gray-700 border-gray-300',
  };

  const complexityColor = complexityColors[approach.complexity_level as keyof typeof complexityColors] || complexityColors.moderate;
  const taskIcon = taskTypeIcons[approach.task_type as keyof typeof taskTypeIcons] || '📋';

  return (
    <div className={`bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden ${className}`}>
      {/* 头部 */}
      <div
        className="bg-gradient-to-r from-indigo-50 to-purple-50 px-6 py-4 border-b border-gray-200 cursor-pointer hover:bg-indigo-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{taskIcon}</span>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">搜索清单</h3>
              <p className="text-sm text-gray-600 mt-0.5">{approach.task_type_description}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${complexityColor}`}>
              {approach.complexity_level}
            </span>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>

      {/* 内容 */}
      {isExpanded && (
        <div className="p-6 space-y-6">
          {/* 所需专业知识 */}
          {approach.required_expertise && approach.required_expertise.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                <span className="mr-2">🎓</span>
                所需专业知识
              </h4>
              <div className="flex flex-wrap gap-2">
                {approach.required_expertise.map((expertise, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm border border-indigo-200"
                  >
                    {expertise}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 搜索清单（v7.290 增强展示） */}
          {approach.solution_steps && approach.solution_steps.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                <span className="mr-2">🗺️</span>
                搜索清单（{approach.solution_steps.length}个任务）
              </h4>
              <div className="space-y-3">
                {approach.solution_steps.map((step: SolutionStep, index: number) => {
                  const priorityColor = priorityColors[(step.priority as keyof typeof priorityColors)] || priorityColors.medium;
                  return (
                    <div
                      key={step.step_id}
                      className="relative pl-8 pb-3 border-l-2 border-indigo-200 last:border-l-0 last:pb-0"
                    >
                      {/* 步骤编号圆点 */}
                      <div className="absolute left-0 top-0 -translate-x-1/2 w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
                        {index + 1}
                      </div>

                      {/* 步骤内容 */}
                      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        {/* 标题行：action + priority */}
                        <div className="flex items-start justify-between mb-2">
                          <div className="font-medium text-gray-900 flex-1">
                            {step.action}
                          </div>
                          {step.priority && (
                            <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium border ${priorityColor}`}>
                              {step.priority}
                            </span>
                          )}
                        </div>

                        {/* 目的 */}
                        <div className="text-sm text-gray-600 mb-2">
                          <span className="font-medium text-gray-700">目的：</span>
                          {step.purpose}
                        </div>

                        {/* 预期产出 */}
                        <div className="text-sm text-indigo-600 bg-indigo-50 rounded px-3 py-2 border border-indigo-100 mb-2">
                          <span className="font-medium">预期产出：</span>
                          {step.expected_output}
                        </div>

                        {/* v7.290: 搜索关键词 */}
                        {step.search_keywords && step.search_keywords.length > 0 && (
                          <div className="mb-2">
                            <span className="text-xs font-medium text-gray-500">关键词：</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {step.search_keywords.map((keyword, kidx) => (
                                <span
                                  key={kidx}
                                  className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs border border-blue-200"
                                >
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* v7.290: 成功标准 */}
                        {step.success_criteria && (
                          <div className="text-xs text-green-700 bg-green-50 rounded px-2 py-1 border border-green-200">
                            <span className="font-medium">✓ 成功标准：</span>
                            {step.success_criteria}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* v7.290: MECE覆盖校验 */}
          {approach.coverage_check && (
            (approach.coverage_check.covered_points?.length > 0 || approach.coverage_check.potentially_missing?.length > 0) && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <span className="mr-2">✅</span>
                  覆盖校验
                </h4>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 space-y-3">
                  {/* 已覆盖 */}
                  {approach.coverage_check.covered_points && approach.coverage_check.covered_points.length > 0 && (
                    <div>
                      <span className="text-sm font-medium text-green-700">✓ 已覆盖：</span>
                      <span className="text-sm text-gray-700 ml-1">
                        {approach.coverage_check.covered_points.join('、')}
                      </span>
                    </div>
                  )}

                  {/* 可能遗漏 */}
                  {approach.coverage_check.potentially_missing && approach.coverage_check.potentially_missing.length > 0 && (
                    <div>
                      <span className="text-sm font-medium text-orange-700">⚠ 可能遗漏：</span>
                      <span className="text-sm text-gray-700 ml-1">
                        {approach.coverage_check.potentially_missing.join('、')}
                      </span>
                    </div>
                  )}

                  {/* 实体覆盖映射 */}
                  {approach.coverage_check.entity_coverage && Object.keys(approach.coverage_check.entity_coverage).length > 0 && (
                    <div className="pt-2 border-t border-gray-200">
                      <span className="text-xs font-medium text-gray-500">实体覆盖：</span>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {Object.entries(approach.coverage_check.entity_coverage).map(([entity, steps]) => (
                          <span
                            key={entity}
                            className="px-2 py-1 bg-white text-gray-700 rounded text-xs border border-gray-300"
                          >
                            {entity} → {steps}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )
          )}

          {/* 关键突破口 */}
          {approach.breakthrough_points && approach.breakthrough_points.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                <span className="mr-2">💡</span>
                关键突破口
              </h4>
              <div className="space-y-3">
                {approach.breakthrough_points.map((bp: BreakthroughPoint, index: number) => (
                  <div
                    key={index}
                    className="bg-amber-50 rounded-lg p-4 border border-amber-200"
                  >
                    <div className="font-medium text-amber-900 mb-2 flex items-start">
                      <span className="mr-2 mt-0.5">🔑</span>
                      <span>{bp.point}</span>
                    </div>
                    <div className="text-sm text-gray-700 ml-6 space-y-1">
                      <div>
                        <span className="font-medium text-gray-800">为什么关键：</span>
                        <span className="text-gray-600">{bp.why_key}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-800">如何利用：</span>
                        <span className="text-gray-600">{bp.how_to_leverage}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 预期产出形态 */}
          {approach.expected_deliverable && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                <span className="mr-2">📦</span>
                预期产出形态
              </h4>
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200 space-y-3">
                {/* 格式 */}
                {approach.expected_deliverable.format && (
                  <div className="flex items-start">
                    <span className="text-sm font-medium text-purple-900 w-20">格式：</span>
                    <span className="text-sm text-purple-700 font-medium">
                      {approach.expected_deliverable.format}
                    </span>
                  </div>
                )}

                {/* 章节 */}
                {approach.expected_deliverable.sections && approach.expected_deliverable.sections.length > 0 && (
                  <div className="flex items-start">
                    <span className="text-sm font-medium text-purple-900 w-20">章节：</span>
                    <div className="flex-1 flex flex-wrap gap-2">
                      {approach.expected_deliverable.sections.map((section, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-white text-purple-700 rounded text-xs border border-purple-200"
                        >
                          {section}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* 关键元素 */}
                {approach.expected_deliverable.key_elements && approach.expected_deliverable.key_elements.length > 0 && (
                  <div className="flex items-start">
                    <span className="text-sm font-medium text-purple-900 w-20">关键元素：</span>
                    <div className="flex-1 text-sm text-purple-700">
                      {approach.expected_deliverable.key_elements.join('、')}
                    </div>
                  </div>
                )}

                {/* 质量标准 */}
                {approach.expected_deliverable.quality_criteria && approach.expected_deliverable.quality_criteria.length > 0 && (
                  <div className="flex items-start">
                    <span className="text-sm font-medium text-purple-900 w-20">质量标准：</span>
                    <div className="flex-1 text-sm text-purple-700">
                      {approach.expected_deliverable.quality_criteria.join('、')}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 任务描述 */}
          <div className="border-t border-gray-200 pt-4">
            <div className="space-y-2">
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase">原始需求</span>
                <p className="text-sm text-gray-700 mt-1">{approach.original_requirement}</p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase">结构化需求</span>
                <p className="text-sm text-gray-700 mt-1">{approach.refined_requirement}</p>
              </div>
            </div>
          </div>

          {/* 置信度和备选方案 */}
          <div className="flex items-center justify-between text-xs text-gray-500 border-t border-gray-200 pt-4">
            <div className="flex items-center space-x-4">
              <span>
                置信度：
                <span className={`font-medium ml-1 ${
                  approach.confidence_score >= 0.8 ? 'text-green-600' :
                  approach.confidence_score >= 0.6 ? 'text-blue-600' :
                  'text-orange-600'
                }`}>
                  {(approach.confidence_score * 100).toFixed(0)}%
                </span>
              </span>
              {approach.alternative_approaches && approach.alternative_approaches.length > 0 && (
                <span>
                  备选方案：{approach.alternative_approaches.length}个
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProblemSolvingApproachCard;
