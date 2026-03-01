'use client';

import React, { useState, useCallback, useMemo } from 'react';
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
import type { EditableSearchStep, Step2SearchPlan, SearchPlanSuggestion, BlockInfo } from '@/types';

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
 * v7.360: 按板块分页显示（Step 1 有 N 个板块，Step 2 就有 N 个分页）
 *
 * 功能：
 * - 按板块分页显示搜索步骤
 * - 添加/删除/编辑步骤
 * - 并行任务指示器
 * - 智能补充建议（用户可忽略）
 * - "运行"按钮启动执行
 *
 * 设计原则：
 * - 任务数量不硬编码，根据问题复杂度动态确定
 * - 支持动态扩展，用户可随时添加新任务
 * - 分页与 Step 1 板块一一对应
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

  // 📊 v7.360: 按板块分页逻辑
  const blocksInfo = plan.blocks_info || [];
  const hasBlocksInfo = blocksInfo.length > 0;

  // 📊 v7.360 调试：打印板块和任务信息
  console.log('📊 [v7.360] blocks_info:', blocksInfo);
  console.log('📊 [v7.360] search_steps serves_blocks:', plan.search_steps.map(s => ({ id: s.id, serves_blocks: s.serves_blocks })));

  // 按板块分组的任务
  const stepsByBlock = useMemo(() => {
    if (!hasBlocksInfo) return {};
    const grouped: Record<string, EditableSearchStep[]> = {};
    // 初始化所有板块
    blocksInfo.forEach(block => {
      grouped[block.id] = [];
    });
    // 分配任务到板块
    plan.search_steps.forEach(step => {
      const blockId = step.serves_blocks?.[0] || blocksInfo[0]?.id;
      console.log(`📊 [v7.360] 任务 ${step.id} serves_blocks=${JSON.stringify(step.serves_blocks)} -> blockId=${blockId}`);
      if (blockId && grouped[blockId]) {
        grouped[blockId].push(step);
      } else if (blocksInfo[0]) {
        // 如果没有匹配的板块，放到第一个板块
        console.log(`📊 [v7.360] 任务 ${step.id} 无匹配板块，放到第一个板块`);
        grouped[blocksInfo[0].id].push(step);
      }
    });
    console.log('📊 [v7.360] stepsByBlock:', Object.entries(grouped).map(([k, v]) => `${k}: ${v.length}个任务`));
    return grouped;
  }, [plan.search_steps, blocksInfo, hasBlocksInfo]);

  // 总页数：按板块数量或传统分页
  const totalPages = hasBlocksInfo
    ? blocksInfo.length
    : Math.max(1, Math.ceil(plan.search_steps.length / 5));

  // 当前板块信息
  const currentBlock = hasBlocksInfo ? blocksInfo[currentPage - 1] : null;
  const currentBlockId = currentBlock?.id || '';

  // 获取当前页的步骤
  const getCurrentPageSteps = useCallback(() => {
    if (hasBlocksInfo && currentBlockId) {
      return stepsByBlock[currentBlockId] || [];
    }
    // 传统分页：每页5个
    const stepsPerPage = 5;
    const start = (currentPage - 1) * stepsPerPage;
    const end = start + stepsPerPage;
    return plan.search_steps.slice(start, end);
  }, [plan.search_steps, currentPage, hasBlocksInfo, currentBlockId, stepsByBlock]);

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
      // 📊 v7.360: 新任务属于当前板块
      serves_blocks: currentBlockId ? [currentBlockId] : [],
    };

    onUpdatePlan({
      ...plan,
      search_steps: [...plan.search_steps, newStep],
      user_added_steps: [...plan.user_added_steps, newStep.id],
    });

    setNewTaskDescription('');
    setNewTaskOutcome('');
    setShowAddForm(false);

    // 📊 v7.360: 按板块分页时不需要跳转，任务会显示在当前板块
    if (!hasBlocksInfo) {
      // 传统分页：跳转到最后一页
      const newTotalPages = Math.ceil((plan.search_steps.length + 1) / 5);
      setCurrentPage(newTotalPages);
    }
  }, [plan, onUpdatePlan, newTaskDescription, newTaskOutcome, currentBlockId, hasBlocksInfo]);

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
    console.log('🔵 [v7.360] handleValidateAndRun 被调用');
    console.log('🔵 [v7.360] onValidate:', typeof onValidate);
    console.log('🔵 [v7.360] onConfirmAndStart:', typeof onConfirmAndStart);

    if (onValidate) {
      console.log('🔵 [v7.360] 调用 onValidate...');
      const result = await onValidate();
      console.log('🔵 [v7.360] onValidate 结果:', result);
      if (result.has_suggestions && result.suggestions.length > 0) {
        setSuggestions(result.suggestions);
        setShowSuggestions(true);
        return;
      }
    }
    console.log('🔵 [v7.360] 调用 onConfirmAndStart...');
    onConfirmAndStart();
  }, [onValidate, onConfirmAndStart]);

  // 忽略建议直接运行
  const handleIgnoreSuggestionsAndRun = useCallback(() => {
    setShowSuggestions(false);
    setSuggestions([]);
    onConfirmAndStart();
  }, [onConfirmAndStart]);

  return (
    <div className="ucppt-card">
      {/* 卡片头部 - 统一样式 */}
      <div className="ucppt-card-header ucppt-card-header-expanded">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-3">
            <div className="ucppt-icon-circle ucppt-icon-blue">
              <ListChecks className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <span className="ucppt-title-blue">搜索任务清单</span>
            </div>
          </div>

          {/* 右侧区域：当前主题 + 分页控件 */}
          <div className="flex items-center gap-3">
            {/* 📊 当前页面搜索主题 */}
            {getCurrentPageSteps().length > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-50 border border-gray-200 dark:border-gray-300 max-w-md">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-600 flex-shrink-0">
                  当前主题:
                </span>
                <span className="text-xs text-gray-700 dark:text-gray-800 truncate font-medium">
                  {currentBlock?.name || getCurrentPageSteps()[0]?.task_description || '搜索任务'}
                </span>
              </div>
            )}

            {/* 📊 v7.360: 分页控件 - 显示板块序号 */}
            {totalPages > 1 && (
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-700" />
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-700 min-w-[3rem] text-center">
                  {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-700" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 任务列表 - 使用统一内容区域 */}
      <div className="ucppt-card-content">
        <div className="space-y-2">
          {/* 🆕 v7.430: 增强加载状态显示 - 骨架屏 + 动态进度 */}
          {plan.is_loading && plan.search_steps.length === 0 && (
            <div className="space-y-4 animate-fade-in">
              {/* 加载指示器 */}
              <div className="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-600">
                <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-4" />
                <p className="text-base font-medium text-gray-700 dark:text-gray-400">
                  {plan.loading_text || '正在生成搜索任务...'}
                </p>
                <p className="text-xs mt-2 text-gray-400 dark:text-gray-500 max-w-md text-center">
                  基于深度分析结果，智能规划搜索方向
                </p>
              </div>

              {/* 骨架屏 - 3个任务卡片占位 */}
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 animate-pulse"
                  >
                    {/* 任务标题骨架 */}
                    <div className="flex items-start gap-3 mb-3">
                      <div className="w-6 h-6 bg-gray-200 dark:bg-gray-700 rounded-full flex-shrink-0" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                        <div className="h-3 bg-gray-100 dark:bg-gray-750 rounded w-full" />
                        <div className="h-3 bg-gray-100 dark:bg-gray-750 rounded w-5/6" />
                      </div>
                    </div>
                    {/* 查询关键词骨架 */}
                    <div className="flex gap-2 mt-3 flex-wrap">
                      <div className="h-6 bg-gray-100 dark:bg-gray-750 rounded-full w-20" />
                      <div className="h-6 bg-gray-100 dark:bg-gray-750 rounded-full w-24" />
                      <div className="h-6 bg-gray-100 dark:bg-gray-750 rounded-full w-16" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 正常任务列表 */}
          {!plan.is_loading && getCurrentPageSteps().map((step, index) => (
            <EditableSearchStepCard
              key={step.id}
              step={step}
              onUpdate={handleUpdateStep}
              onDelete={handleDeleteStep}
              isReadOnly={isReadOnly}
              displayIndex={index + 1}
            />
          ))}

          {/* 空状态（非加载中） */}
          {!plan.is_loading && plan.search_steps.length === 0 && (
            <div className="text-center py-8 text-gray-500 dark:text-gray-600">
              <ListChecks className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">暂无搜索任务</p>
              <p className="text-xs mt-1">点击下方按钮添加任务</p>
            </div>
          )}
        </div>
      </div>

      {/* 添加任务表单 */}
      {showAddForm && (
        <div className="ucppt-card-content">
          <div className="p-4 rounded-lg border-2 border-dashed border-blue-300 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/20">
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-700 mb-1">
                  搜索任务描述
                </label>
                <textarea
                  value={newTaskDescription}
                  onChange={(e) => setNewTaskDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-400 bg-white dark:bg-white text-sm text-gray-900 dark:text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={2}
                  placeholder="描述要搜索的内容..."
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-700 mb-1">
                  期望结果（可选）
                </label>
                <textarea
                  value={newTaskOutcome}
                  onChange={(e) => setNewTaskOutcome(e.target.value)}
                  className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-400 bg-white dark:bg-white text-sm text-gray-900 dark:text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
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
                  className="px-3 py-1.5 rounded text-sm text-gray-600 dark:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-100 transition-colors"
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
        <div className="ucppt-card-content">
          <div className="p-4 rounded-lg border border-orange-200 dark:border-orange-700 bg-orange-50 dark:bg-orange-900/20">
            <div className="flex items-start gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-orange-500 dark:text-orange-400 flex-shrink-0 mt-0.5" />
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
                  className="flex items-center justify-between p-2 rounded bg-white dark:bg-white border border-orange-100 dark:border-orange-200"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 dark:text-gray-900 truncate">
                      {suggestion.direction}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-600 truncate">
                      {suggestion.why_important}
                    </p>
                  </div>
                  <button
                    onClick={() => handleAddFromSuggestion(suggestion)}
                    className="ml-2 px-2 py-1 rounded bg-orange-100 dark:bg-orange-900/30 hover:bg-orange-200 dark:hover:bg-orange-900/50 text-orange-600 dark:text-orange-400 text-xs transition-colors"
                  >
                    添加
                  </button>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={handleIgnoreSuggestionsAndRun}
                className="px-3 py-1.5 rounded text-sm text-gray-600 dark:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-100 transition-colors"
              >
                忽略并运行
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 底部操作栏 */}
      <div className="ucppt-card-content">
        <div className="flex items-center justify-end gap-2">
          {/* 操作按钮 */}
          {!isReadOnly && (
            <button
              onClick={() => setShowAddForm(true)}
              disabled={showAddForm}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-gray-300 dark:border-gray-400 hover:bg-gray-100 dark:hover:bg-gray-100 text-sm text-gray-700 dark:text-gray-800 transition-colors disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              添加任务
            </button>
          )}

          {!isReadOnly && (
            <button
              onClick={handleValidateAndRun}
              disabled={isConfirming || isValidating || plan.search_steps.length === 0}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
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
  );
};

export default Step2TaskListEditor;
