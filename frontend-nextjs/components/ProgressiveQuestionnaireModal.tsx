// components/ProgressiveQuestionnaireModal.tsx
// 三步递进式问卷 Modal 组件
//
// ⚠️ **已废弃 (DEPRECATED)** - 2026-01-02
//
// 废弃原因：
// 1. 功能不完整，缺少以下v7.106新增功能：
//    - ❌ 动机类型标签（12种动机类型）
//    - ❌ AI推理说明
//    - ❌ 关键词标签
//    - ❌ 依赖关系显示
//    - ❌ 任务编辑功能
//
// 2. 历史问题记录：
//    - 2026-01-02: 用户发现依赖关系不显示，定位到使用了本简化版组件
//    - 详见：QUESTIONNAIRE_UI_FIX.md
//
// 替代方案：
// ✅ 使用 UnifiedProgressiveQuestionnaireModal.tsx（完整版）
//    import { UnifiedProgressiveQuestionnaireModal } from '@/components/UnifiedProgressiveQuestionnaireModal';
//
// 功能对比：
// | 功能           | 简化版(本文件) | 完整版              |
// |----------------|---------------|---------------------|
// | 基础问卷       | ✅            | ✅                  |
// | 动机类型标签   | ❌            | ✅ (12种类型)       |
// | AI推理说明     | ❌            | ✅                  |
// | 关键词标签     | ❌            | ✅                  |
// | 依赖关系       | ❌            | ✅ (#ID + 标题)     |
// | 任务编辑       | ❌            | ✅                  |
// | 执行顺序       | ❌            | ✅                  |
//
// 如果你看到此文件被导入，请立即修改为：
// - import { ProgressiveQuestionnaireModal } from '@/components/ProgressiveQuestionnaireModal';  // ❌ 错误
// + import { UnifiedProgressiveQuestionnaireModal } from '@/components/UnifiedProgressiveQuestionnaireModal';  // ✅ 正确
//
// 并更新组件使用：
// - <ProgressiveQuestionnaireModal {...props} />  // ❌ 错误
// + <UnifiedProgressiveQuestionnaireModal {...props} />  // ✅ 正确
//
// 注意：此文件暂时保留用于紧急回退，计划于 2026-02-01 完全删除。

'use client';

import { CheckCircle2, SkipForward } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js';

// 注册 Chart.js 组件
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

interface ProgressiveQuestionnaireModalProps {
  isOpen: boolean;
  data: any;
  onConfirm: (data?: any) => void;
  onSkip: () => void;
}

export function ProgressiveQuestionnaireModal({
  isOpen,
  data,
  onConfirm,
  onSkip
}: ProgressiveQuestionnaireModalProps) {
  // 雷达图维度值状态（Step 2）
  const [dimensionValues, setDimensionValues] = useState<Record<string, number>>({});

  // 问题答案状态（Step 3）
  const [answers, setAnswers] = useState<Record<string, any>>({});

  // 初始化维度默认值（Step 2）
  // ⚠️ useEffect 必须在条件返回之前调用（React Hooks 规则）
  useEffect(() => {
    if (data?.dimensions && data.dimensions.length > 0 && Object.keys(dimensionValues).length === 0) {
      const initialValues: Record<string, number> = {};
      data.dimensions.forEach((dim: any) => {
        initialValues[dim.id || dim.dimension_id] = dim.default_value || 50;
      });
      setDimensionValues(initialValues);
    }
  }, [data?.dimensions, dimensionValues]);

  // 条件返回必须在所有 Hooks 之后
  if (!isOpen || !data) return null;

  const {
    step,
    total_steps,
    title,
    message,
    extracted_tasks,
    user_input_summary,
    dimensions, // Step 2 数据
    questionnaire // Step 3 数据
  } = data;

  // 渲染 Step 1: 任务梳理
  const renderStep1Content = () => (
    <>
      {/* 用户输入摘要 */}
      {user_input_summary && (
        <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700 rounded-lg">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">您的需求</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">{user_input_summary}</p>
        </div>
      )}

      {/* 核心任务列表 */}
      {extracted_tasks && extracted_tasks.length > 0 && (
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">
            识别到的核心任务
          </h3>
          <div className="space-y-3">
            {extracted_tasks.map((task: any, index: number) => (
              <div
                key={task.id || index}
                className="bg-gray-50 dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded flex items-center justify-center text-sm font-medium">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
                      {task.title || task.name || '任务'}
                    </h4>
                    {task.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">{task.description}</p>
                    )}
                    {task.priority && (
                      <span className="inline-block mt-2 px-2 py-1 bg-gray-200 dark:bg-gray-700 text-xs text-gray-700 dark:text-gray-300 rounded">
                        优先级: {task.priority}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 提示信息 */}
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          您可以确认这些任务，或选择跳过问卷直接进入分析流程。
        </p>
      </div>
    </>
  );

  // 渲染 Step 2: 雷达图维度偏好
  const renderStep2Content = () => {
    if (!dimensions || dimensions.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          暂无可用的维度数据
        </div>
      );
    }

    // 准备雷达图数据
    const radarData = {
      labels: dimensions.map((d: any) => d.name),
      datasets: [
        {
          label: '您的偏好',
          data: dimensions.map((d: any) => dimensionValues[d.id || d.dimension_id] || 50),
          backgroundColor: 'rgba(59, 130, 246, 0.2)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 2,
          pointBackgroundColor: 'rgb(59, 130, 246)',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: 'rgb(59, 130, 246)'
        }
      ]
    };

    const radarOptions = {
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          ticks: {
            stepSize: 20,
            display: false
          },
          grid: {
            color: 'rgba(156, 163, 175, 0.2)'
          }
        }
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          enabled: true,
          callbacks: {
            label: function(context: any) {
              const index = context.dataIndex;
              const dim = dimensions[index];
              const value = context.parsed.r;
              const leftLabel = dim.left_label || '';
              const rightLabel = dim.right_label || '';

              if (value < 30) {
                return `${leftLabel} (${value})`;
              } else if (value > 70) {
                return `${rightLabel} (${value})`;
              } else {
                return `${leftLabel} ← ${value} → ${rightLabel}`;
              }
            }
          }
        }
      },
      maintainAspectRatio: true,
      responsive: true
    };

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧：滑块列表 */}
        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
          {dimensions.map((dimension: any, index: number) => {
            const dimId = dimension.id || dimension.dimension_id;
            const value = dimensionValues[dimId] || 50;

            return (
              <div key={dimId} className="bg-gray-50 dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {dimension.name}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {value}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-600 dark:text-gray-400 min-w-[80px] text-left">
                    {dimension.left_label}
                  </span>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={value}
                    onChange={(e) => setDimensionValues(prev => ({
                      ...prev,
                      [dimId]: parseInt(e.target.value)
                    }))}
                    className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />

                  <span className="text-xs text-gray-600 dark:text-gray-400 min-w-[80px] text-right">
                    {dimension.right_label}
                  </span>
                </div>

                {dimension.description && (
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    {dimension.description}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* 右侧：雷达图可视化 */}
        <div className="flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">
            偏好雷达图
          </h3>
          <div className="w-full max-w-md">
            <Radar data={radarData} options={radarOptions} />
          </div>
        </div>
      </div>
    );
  };

  // 渲染 Step 3: 补充问题
  const renderStep3Content = () => {
    if (!questionnaire || !questionnaire.questions || questionnaire.questions.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          无需补充问题，信息已完整
        </div>
      );
    }

    const questions = questionnaire.questions;

    return (
      <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
        {questions.map((question: any, index: number) => {
          const questionId = question.id || `q_${index}`;
          const isRequired = question.is_required || false;

          return (
            <div key={questionId} className="bg-gray-50 dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-start gap-2 mb-3">
                {isRequired && (
                  <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-medium rounded">
                    必答
                  </span>
                )}
                <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex-1">
                  {index + 1}. {question.question}
                </h4>
              </div>

              {/* 单选题 */}
              {question.type === 'single_choice' && question.options && (
                <div className="space-y-2">
                  {question.options.map((option: string, optIdx: number) => (
                    <label key={optIdx} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name={questionId}
                        value={option}
                        checked={answers[questionId] === option}
                        onChange={(e) => setAnswers(prev => ({ ...prev, [questionId]: e.target.value }))}
                        className="w-4 h-4 text-blue-600 accent-blue-600"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{option}</span>
                    </label>
                  ))}
                </div>
              )}

              {/* 多选题 */}
              {question.type === 'multiple_choice' && question.options && (
                <div className="space-y-2">
                  {question.options.map((option: string, optIdx: number) => (
                    <label key={optIdx} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        value={option}
                        checked={(answers[questionId] || []).includes(option)}
                        onChange={(e) => {
                          const current = answers[questionId] || [];
                          const updated = e.target.checked
                            ? [...current, option]
                            : current.filter((v: string) => v !== option);
                          setAnswers(prev => ({ ...prev, [questionId]: updated }));
                        }}
                        className="w-4 h-4 text-blue-600 accent-blue-600 rounded"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{option}</span>
                    </label>
                  ))}
                </div>
              )}

              {/* 开放题 */}
              {question.type === 'open_ended' && (
                <textarea
                  value={answers[questionId] || ''}
                  onChange={(e) => setAnswers(prev => ({ ...prev, [questionId]: e.target.value }))}
                  placeholder="请输入您的回答..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                />
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // 根据步骤渲染内容
  const renderContent = () => {
    switch (step) {
      case 1:
        return renderStep1Content();
      case 2:
        return renderStep2Content();
      case 3:
        return renderStep3Content();
      default:
        return <div>未知步骤</div>;
    }
  };

  // 确认按钮处理
  const handleConfirm = () => {
    if (step === 2) {
      // Step 2: 传递维度值
      onConfirm({ dimension_values: dimensionValues });
    } else if (step === 3) {
      // Step 3: 传递答案
      onConfirm({ answers });
    } else {
      // Step 1: 无额外数据
      onConfirm();
    }
  };

  // 确认按钮文本
  const getConfirmButtonText = () => {
    switch (step) {
      case 1:
        return '确认任务列表';
      case 2:
        return '确认偏好设置';
      case 3:
        return '提交问卷';
      default:
        return '确认';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white dark:bg-[var(--card-bg)] rounded-xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-gray-200 dark:border-[var(--border-color)]">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-[var(--border-color)] px-6 py-5 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm font-medium rounded-full">
                步骤 {step}/{total_steps}
              </span>
            </div>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{message}</p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {renderContent()}
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-200 dark:border-[var(--border-color)] px-6 py-4 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-end gap-3">
          <button
            onClick={onSkip}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
          >
            <SkipForward className="w-4 h-4" />
            <span>跳过问卷</span>
          </button>
          <button
            onClick={handleConfirm}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{getConfirmButtonText()}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
