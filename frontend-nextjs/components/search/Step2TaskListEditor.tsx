'use client';

import React, { useState, useCallback } from 'react';
import {
  Plus,
  Play,
  ChevronLeft,
  ChevronRight,
  Zap,
  ListChecks,
  AlertCircle,
  Loader2,
  Check,
  X,
} from 'lucide-react';
import EditableSearchStepCard from './EditableSearchStepCard';
import type { EditableSearchStep, Step2SearchPlan, SearchPlanSuggestion } from '@/types';

interface Step2TaskListEditorProps {
  plan: Step2SearchPlan;
  onUpdatePlan: (plan: Step2SearchPlan) => void;
  onConfirmAndStart: () => void;
  onValidate?: () => Promise<{ has_suggestions: boolean; suggestions: SearchPlanSuggestion[] }>;
  isConfirming?: boolean;
  isValidating?: boolean;
  isReadOnly?: boolean;
}

/**
 * v7.300: 第2步搜索任务列表编辑器
 *
 * 功能：
 * - 分页显示搜索步骤
 * - 添加/删除/编辑步骤
 * - 并行任务指示器
 * - 智能补充建议（用户可忽略）
 * - "运行"按钮启动执行
 *
 * 设计原则：
 * - 任务数量不硬编码，根据问题复杂度动态确定
 * - 支持动态扩展，用户可随时添加新任务
 */
const Step2TaskListEditor: React.FC<Step2TaskListEditorProps> = ({
  plan,
  onUpdatePlan,
  onConfirmAndStart,
  onValidate,
  isConfirming = false,
  isValidating = false,
  isReadOnly = false,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTaskDescription, setNewTaskDescription] = useState('');
  const [newTaskOutcome, setNewTaskOutcome] = useState('');
  const [suggestions, setSuggestions] = useState<SearchPlanSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const stepsPerPage = 5;
  const totalPages = Math.max(1, Math.ceil(plan.search_steps.length / stepsPerPage));

  // 获取当前页的步骤
  const getCurrentPageSteps = useCallback(() => {
    const start = (currentPage - 1) * stepsPerPage;
    const end = start + stepsPerPage;
    return plan.search_steps.slice(start, end);
  }, [plan.search_steps, currentPage, stepsPerPage]);

  // 计算并行任务数量
  const parallelCount = plan.search_steps.filter(
    (s) => s.can_parallel && s.status === 'pending'
  ).length;

  // 更新步骤
  const handleUpdateStep = useCallback(
    (stepId: string, updates: Partial<EditableSearchStep>) => {
      const updatedSteps = plan.search_steps.map((step) =>
        step.id === stepId ? { ...step, ...updates, is_user_modified: true } : step
      );
      // 使用 Array.from 替代 spread 操作符以避免 downlevelIteration 问题
      const modifiedSet = new Set([...plan.user_modified_steps, stepId]);
      onUpdatePlan({
        ...plan,
        search_steps: updatedSteps,
        user_modified_steps: Array.from(modifiedSet),
      });
    },
    [plan, onUpdatePlan]
  );

  // 删除步骤
  const handleDeleteStep = useCallback(
    (stepId: string) => {
      const updatedSteps = plan.search_steps
        .filter((step) => step.id !== stepId)
        .map((step, idx) => ({ ...step, step_number: idx + 1 }));
      onUpdatePlan({
        ...plan,
        search_steps: updatedSteps,
        user_deleted_steps: [...plan.user_deleted_steps, stepId],
      });
    },
    [plan, onUpdatePlan]
  );

  // 添加新步骤
  const handleAddStep = useCallback(() => {
    if (!newTaskDescription.trim()) return;

    const newStep: EditableSearchStep = {
      id: `S${plan.search_steps.length + 1}`,
      step_number: plan.search_steps.length + 1,
      task_description: newTaskDescription.trim(),
      expected_outcome: newTaskOutcome.trim(),
      search_keywords: [],
      priority: 'medium',
      can_parallel: true,
      status: 'pending',
      completion_score: 0,
      is_user_added: true,
    };

    onUpdatePlan({
      ...plan,
      search_steps: [...plan.search_steps, newStep],
      user_added_steps: [...plan.user_added_steps, newStep.id],
    });

    setNewTaskDescription('');
    setNewTaskOutcome('');
    setShowAddForm(false);

    // 跳转到最后一页
    const newTotalPages = Math.ceil((plan.search_steps.length + 1) / stepsPerPage);
    setCurrentPage(newTotalPages);
  }, [plan, onUpdatePlan, newTaskDescription, newTaskOutcome, stepsPerPage]);

  // 从建议添加步骤
  const handleAddFromSuggestion = useCallback(
    (suggestion: SearchPlanSuggestion) => {
      const newStep: EditableSearchStep = {
        id: `S${plan.search_steps.length + 1}`,
        step_number: plan.search_steps.length + 1,
        task_description: suggestion.what_to_search,
        expected_outcome: suggestion.why_important,
        search_keywords: [],
        priority: suggestion.priority === 'P0' ? 'high' : suggestion.priority === 'P1' ? 'medium' : 'low',
        can_parallel: true,
        status: 'pending',
        completion_score: 0,
        is_user_added: true,
      };

      onUpdatePlan({
        ...plan,
        search_steps: [...plan.search_steps, newStep],
        user_added_steps: [...plan.user_added_steps, newStep.id],
      });

      // 从建议列表中移除
      setSuggestions((prev) => prev.filter((s) => s.direction !== suggestion.direction));
    },
    [plan, onUpdatePlan]
  );

  // 验证并获取建议
  const handleValidateAndRun = useCallback(async () => {
    if (onValidate) {
      const result = await onValidate();
      if (result.has_suggestions && result.suggestions.length > 0) {
        setSuggestions(result.suggestions);
        setShowSuggestions(true);
        return;
      }
    }
    onConfirmAndStart();
  }, [onValidate, onConfirmAndStart]);

  // 忽略建议直接运行
  const handleIgnoreSuggestionsAndRun = useCallback(() => {
    setShowSuggestions(false);
    setSuggestions([]);
    onConfirmAndStart();
  }, [onConfirmAndStart]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* 头部 */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
              <ListChecks className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                搜索任务清单
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                共 {plan.search_steps.length} 个任务 · 可编辑、删除或添加
              </p>
            </div>
          </div>

          {/* 并行指示器 */}
          {parallelCount > 1 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 text-xs">
              <Zap className="w-3.5 h-3.5" />
              <span>并行处理 {parallelCount} 个节点</span>
            </div>
          )}
        </div>
      </div>

      {/* 任务列表 */}
      <div className="p-4 space-y-3">
        {getCurrentPageSteps().map((step) => (
          <EditableSearchStepCard
            key={step.id}
            step={step}
            onUpdate={handleUpdateStep}
            onDelete={handleDeleteStep}
            isReadOnly={isReadOnly}
          />
        ))}

        {/* 空状态 */}
        {plan.search_steps.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <ListChecks className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">暂无搜索任务</p>
            <p className="text-xs mt-1">点击下方按钮添加任务</p>
          </div>
        )}
      </div>

      {/* 添加任务表单 */}
      {showAddForm && (
        <div className="px-4 pb-4">
          <div className="p-4 rounded-lg border-2 border-dashed border-blue-300 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/10">
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  搜索任务描述
                </label>
                <textarea
                  value={newTaskDescription}
                  onChange={(e) => setNewTaskDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={2}
                  placeholder="描述要搜索的内容..."
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  期望结果（可选）
                </label>
                <textarea
                  value={newTaskOutcome}
                  onChange={(e) => setNewTaskOutcome(e.target.value)}
                  className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={2}
                  placeholder="期望获得什么信息..."
                />
              </div>
              <div className="flex items-center justify-end gap-2">
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setNewTaskDescription('');
                    setNewTaskOutcome('');
                  }}
                  className="px-3 py-1.5 rounded text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleAddStep}
                  disabled={!newTaskDescription.trim()}
                  className="px-3 py-1.5 rounded bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm transition-colors"
                >
                  添加
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 智能补充建议 */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="px-4 pb-4">
          <div className="p-4 rounded-lg border border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/20">
            <div className="flex items-start gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-orange-700 dark:text-orange-400">
                  发现可能遗漏的搜索方向
                </p>
                <p className="text-xs text-orange-600 dark:text-orange-500 mt-0.5">
                  以下是系统建议补充的任务，您可以选择添加或忽略
                </p>
              </div>
            </div>
            <div className="space-y-2 mb-3">
              {suggestions.map((suggestion, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded bg-white dark:bg-gray-800 border border-orange-100 dark:border-orange-900"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 dark:text-gray-200 truncate">
                      {suggestion.direction}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {suggestion.why_important}
                    </p>
                  </div>
                  <button
                    onClick={() => handleAddFromSuggestion(suggestion)}
                    className="ml-2 px-2 py-1 rounded bg-orange-100 hover:bg-orange-200 dark:bg-orange-900/30 dark:hover:bg-orange-900/50 text-orange-600 dark:text-orange-400 text-xs transition-colors"
                  >
                    添加
                  </button>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={handleIgnoreSuggestionsAndRun}
                className="px-3 py-1.5 rounded text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                忽略并运行
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 底部操作栏 */}
      <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <div className="flex items-center justify-between">
          {/* 分页 */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-2">
            {!isReadOnly && (
              <button
                onClick={() => setShowAddForm(true)}
                disabled={showAddForm}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-sm text-gray-700 dark:text-gray-300 transition-colors disabled:opacity-50"
              >
                <Plus className="w-4 h-4" />
                添加任务
              </button>
            )}

            {!isReadOnly && (
              <button
                onClick={handleValidateAndRun}
                disabled={isConfirming || isValidating || plan.search_steps.length === 0}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
              >
                {isValidating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    检查中...
                  </>
                ) : isConfirming ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    启动中...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    运行
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Step2TaskListEditor;
