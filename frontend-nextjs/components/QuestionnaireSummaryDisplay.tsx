// components/QuestionnaireSummaryDisplay.tsx
// v7.147: 问卷汇总展示组件 - 显示重构后的需求文档
// v7.151: 升级为"需求洞察"组件
//   - 新增项目本质、隐性需求、关键冲突展示
//   - 默认展开风险和洞察区块
//   - 添加"修改理解"按钮支持用户编辑
// v7.154: 移除内部确认按钮，通过 forwardRef 暴露 getModifications 方法

'use client';

import { useState, forwardRef, useImperativeHandle } from 'react';
import { ChevronDown, ChevronUp, Target, AlertTriangle, TrendingUp, Zap, CheckCircle2, Info, Edit3, Lightbulb, AlertCircle } from 'lucide-react';
import type { RestructuredRequirements } from '@/types';

interface QuestionnaireSummaryDisplayProps {
  data: RestructuredRequirements;
  summaryText?: string;
  onConfirm: (modifications?: Record<string, string>) => void;
  onBack?: () => void;
}

// 🆕 v7.154: 暴露给父组件的方法
export interface QuestionnaireSummaryDisplayRef {
  getModifications: () => Record<string, string> | undefined;
}

export const QuestionnaireSummaryDisplay = forwardRef<QuestionnaireSummaryDisplayRef, QuestionnaireSummaryDisplayProps>(
  function QuestionnaireSummaryDisplay({
    data,
    summaryText,
    onConfirm,
    onBack
  }, ref) {
  // 🆕 v7.151: 默认展开风险和洞察
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    essence: true,       // 🆕 项目本质
    objectives: true,
    constraints: true,
    priorities: true,
    conflicts: true,     // 🆕 关键冲突
    risks: true,         // 🔧 v7.151: 默认展开
    insights: true,      // 🔧 v7.151: 默认展开
    implicit: false      // 🆕 隐性需求
  });

  // 🆕 v7.151: 编辑模式状态
  const [isEditing, setIsEditing] = useState(false);
  const [editedGoal, setEditedGoal] = useState(data.project_objectives?.primary_goal || '');

  // 🆕 v7.154: 暴露 getModifications 方法给父组件
  useImperativeHandle(ref, () => ({
    getModifications: () => {
      if (isEditing && editedGoal !== data.project_objectives?.primary_goal) {
        return { primary_goal: editedGoal };
      }
      return undefined;
    }
  }), [isEditing, editedGoal, data.project_objectives?.primary_goal]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getSeverityColor = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-blue-600 bg-blue-50';
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 - 🆕 v7.151: 更名为需求洞察 */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          需求洞察
        </h2>
        <p className="text-sm text-gray-600">
          ✅ 需求洞察完成！AI 已深度分析您的需求，请确认或编辑
        </p>
      </div>

      {/* 🆕 v7.151: 项目本质（新增区块） */}
      {data.project_essence && (
        <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Lightbulb className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">项目本质</h3>
              <p className="text-gray-700 leading-relaxed italic">
                &ldquo;{data.project_essence}&rdquo;
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 执行摘要 - 一句话总结 */}
      {data.executive_summary?.one_sentence && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Zap className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">项目核心</h3>
              <p className="text-gray-700 leading-relaxed">
                {data.executive_summary.one_sentence}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 🆕 v7.151: ⚠️ 请重点关注区块 */}
      {((data.key_conflicts?.length ?? 0) > 0 || data.identified_risks?.some(r => r.severity === 'high')) && (
        <div className="bg-amber-50 border-2 border-amber-300 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            <h3 className="font-bold text-amber-800">⚠️ 请重点关注</h3>
          </div>
          <div className="space-y-2 text-sm">
            {data.key_conflicts?.slice(0, 2).map((conflict: any, idx: number) => (
              <div key={idx} className="flex items-start gap-2">
                <span className="text-amber-600">•</span>
                <span className="text-gray-700">{conflict.conflict}</span>
              </div>
            ))}
            {data.identified_risks?.filter(r => r.severity === 'high').slice(0, 2).map((risk, idx) => (
              <div key={`risk-${idx}`} className="flex items-start gap-2">
                <span className="text-red-600">⚠</span>
                <span className="text-gray-700">{risk.risk || risk.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 项目目标 - 🆕 v7.151: 支持编辑 */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => toggleSection('objectives')}
          className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Target className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-gray-900">项目目标</h3>
            {/* 🆕 v7.151: 编辑按钮 */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(!isEditing);
              }}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" />
              {isEditing ? '取消编辑' : '修改理解'}
            </button>
          </div>
          {expandedSections.objectives ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </button>

        {expandedSections.objectives && (
          <div className="p-4 bg-gray-50 border-t border-gray-200 space-y-3">
            {/* 🆕 v7.151: 用户表达 vs AI理解对比 */}
            {data.project_objectives.understanding_comparison && (
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-xs font-medium text-gray-500">用户表达</span>
                    <p className="mt-1 text-gray-700">{data.project_objectives.understanding_comparison.user_expression}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-gray-500">AI 理解</span>
                    <p className="mt-1 text-gray-700">{data.project_objectives.understanding_comparison.ai_understanding}</p>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2 italic">
                  {data.project_objectives.understanding_comparison.alignment_note}
                </p>
              </div>
            )}

            <div>
              <span className="text-xs font-medium text-gray-500 uppercase">核心目标</span>
              {isEditing ? (
                <textarea
                  value={editedGoal}
                  onChange={(e) => setEditedGoal(e.target.value)}
                  className="mt-1 w-full p-2 border border-blue-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                />
              ) : (
                <p className="mt-1 text-gray-900">{data.project_objectives.primary_goal}</p>
              )}
              <span className="text-xs text-gray-500 mt-1 inline-block">
                来源: {data.project_objectives.primary_goal_source}
              </span>
            </div>

            {data.project_objectives.secondary_goals?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase">次要目标</span>
                <ul className="mt-1 space-y-1">
                  {data.project_objectives.secondary_goals.map((goal, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                      <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                      <span>{goal}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {data.project_objectives.success_criteria?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase">成功标准</span>
                <ul className="mt-1 space-y-1">
                  {data.project_objectives.success_criteria.map((criterion, idx) => (
                    <li key={idx} className="text-sm text-gray-700">• {criterion}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 约束条件 */}
      {(data.constraints.budget || data.constraints.timeline || data.constraints.space) && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('constraints')}
            className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Info className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">约束条件</h3>
            </div>
            {expandedSections.constraints ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {expandedSections.constraints && (
            <div className="p-4 bg-gray-50 border-t border-gray-200 space-y-3">
              {data.constraints.budget && (
                <div>
                  <span className="text-xs font-medium text-gray-500 uppercase">预算</span>
                  <p className="mt-1 text-gray-900">{data.constraints.budget.total}</p>
                  {data.constraints.budget.flexibility && (
                    <p className="text-xs text-gray-600 mt-1">灵活度: {data.constraints.budget.flexibility}</p>
                  )}
                </div>
              )}

              {data.constraints.timeline && (
                <div>
                  <span className="text-xs font-medium text-gray-500 uppercase">时间</span>
                  <p className="mt-1 text-gray-900">{data.constraints.timeline.duration}</p>
                  {data.constraints.timeline.urgency && (
                    <p className="text-xs text-gray-600 mt-1">紧急程度: {data.constraints.timeline.urgency}</p>
                  )}
                </div>
              )}

              {data.constraints.space && (
                <div>
                  <span className="text-xs font-medium text-gray-500 uppercase">空间</span>
                  <p className="mt-1 text-gray-900">{data.constraints.space.area}</p>
                  {data.constraints.space.layout && (
                    <p className="text-xs text-gray-600 mt-1">布局: {data.constraints.space.layout}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 设计重点 */}
      {data.design_priorities?.length > 0 && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('priorities')}
            className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900">设计重点</h3>
              <span className="text-xs text-gray-500">({data.design_priorities.length} 个维度)</span>
            </div>
            {expandedSections.priorities ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {expandedSections.priorities && (
            <div className="p-4 bg-gray-50 border-t border-gray-200 space-y-3">
              {data.design_priorities.map((priority: any, idx: number) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{priority.label}</span>
                    <span className="text-xs text-gray-500">{Math.round(priority.weight * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all"
                      style={{ width: `${priority.weight * 100}%` }}
                    />
                  </div>
                  {(priority.tendency || priority.key_requirements) && (
                    <p className="text-xs text-gray-600">
                      {priority.tendency || (Array.isArray(priority.key_requirements) ? priority.key_requirements.join('、') : priority.key_requirements)}
                    </p>
                  )}
                  {priority.rationale && (
                    <p className="text-xs text-gray-500 italic">{priority.rationale}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 识别风险 */}
      {data.identified_risks?.length > 0 && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('risks')}
            className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              <h3 className="font-semibold text-gray-900">识别风险</h3>
              <span className="text-xs text-gray-500">({data.identified_risks.length} 项)</span>
            </div>
            {expandedSections.risks ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {expandedSections.risks && (
            <div className="p-4 bg-gray-50 border-t border-gray-200 space-y-2">
              {data.identified_risks.map((risk, idx) => (
                <div key={idx} className="bg-white border border-gray-200 rounded p-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{risk.description || risk.risk}</span>
                    <span className={`text-xs px-2 py-1 rounded-full ${getSeverityColor(risk.severity)}`}>
                      {risk.severity === 'high' ? '高' : risk.severity === 'medium' ? '中' : '低'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600">缓解措施: {risk.mitigation}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 洞察摘要 - 🔧 v7.152: 增强空数据降级展示 */}
      {data.insight_summary && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('insights')}
            className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-indigo-600" />
              <h3 className="font-semibold text-gray-900">AI 洞察</h3>
              {/* 🔧 v7.152: 智能显示锐度评分状态 */}
              <span className={`text-xs ${
                data.insight_summary.L5_sharpness_score < 0
                  ? 'text-amber-600 bg-amber-50 px-2 py-0.5 rounded'
                  : data.insight_summary.L5_sharpness_score === 0
                    ? 'text-red-500'
                    : 'text-gray-500'
              }`}>
                {data.insight_summary.L5_sharpness_score < 0
                  ? '⏳ 生成中...'
                  : data.insight_summary.L5_sharpness_score === 0
                    ? '⚠️ 待分析'
                    : `锐度评分: ${data.insight_summary.L5_sharpness_score}/10`
                }
              </span>
            </div>
            {expandedSections.insights ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {expandedSections.insights && (
            <div className="p-4 bg-gray-50 border-t border-gray-200 space-y-3 text-sm">
              {/* 🔧 v7.152: 检测空洞察状态 */}
              {(!data.insight_summary.L4_project_task_jtbd &&
                !data.insight_summary.L3_core_tension &&
                data.insight_summary.L5_sharpness_score <= 0) ? (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center">
                  <AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                  <p className="text-amber-800 font-medium">
                    {data.insight_summary._status === 'pending'
                      ? '🔄 洞察正在生成中，请稍候...'
                      : '⚠️ 洞察生成失败'}
                  </p>
                  <p className="text-amber-600 text-xs mt-1">
                    {data.insight_summary._status === 'pending'
                      ? '系统正在分析您的需求，这可能需要几秒钟'
                      : '可能是分析层数据不足，系统已使用基础分析模式'}
                  </p>
                </div>
              ) : (
                <>
                  {data.insight_summary.L4_project_task_jtbd && (
                    <div>
                      <span className="text-xs font-medium text-gray-500 uppercase">核心任务 (JTBD)</span>
                      <p className="mt-1 text-gray-700">{data.insight_summary.L4_project_task_jtbd}</p>
                    </div>
                  )}

                  {data.insight_summary.L3_core_tension && (
                    <div>
                      <span className="text-xs font-medium text-gray-500 uppercase">核心张力</span>
                      <p className="mt-1 text-gray-700">{data.insight_summary.L3_core_tension}</p>
                    </div>
                  )}

                  {data.insight_summary.L5_sharpness_note && (
                    <div>
                      <span className="text-xs font-medium text-gray-500 uppercase">锐度说明</span>
                      <p className="mt-1 text-gray-600 italic">{data.insight_summary.L5_sharpness_note}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* 元数据 - 🆕 v7.151: 显示LLM增强标记 */}
      <div className="text-center text-xs text-gray-400 pt-2">
        生成于 {new Date(data.metadata.generated_at).toLocaleString('zh-CN')} |
        方法: {data.metadata.generation_method}
        {data.metadata.llm_enhanced && ' | 🧠 LLM增强'}
      </div>
    </div>
  );
});
