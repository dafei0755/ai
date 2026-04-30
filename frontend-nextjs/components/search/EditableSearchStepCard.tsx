'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Edit3,
  Trash2,
  Check,
  X,
  GripVertical,
  Loader2,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Clock,
} from 'lucide-react';
import type { EditableSearchStep } from '@/types';

interface EditableSearchStepCardProps {
  step: EditableSearchStep;
  onUpdate: (stepId: string, updates: Partial<EditableSearchStep>) => void;
  onDelete: (stepId: string) => void;
  isReadOnly?: boolean;
  showDragHandle?: boolean;
  /** 页面内的显示序号（每页独立编号，从1开始） */
  displayIndex?: number;
}

/**
 * v7.300: 可编辑的搜索步骤卡片
 * v7.360: 添加内联搜索状态和结果展示
 *
 * 功能：
 * - 点击编辑任务描述和期望结果
 * - 删除步骤
 * - 显示优先级和并行状态
 * - 显示执行状态（pending/searching/complete）
 * - 📊 v7.360: 内联显示搜索进度和结果
 */
const EditableSearchStepCard: React.FC<EditableSearchStepCardProps> = ({
  step,
  onUpdate,
  onDelete,
  isReadOnly = false,
  showDragHandle = false,
  displayIndex,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedDescription, setEditedDescription] = useState(step.task_description);
  const [editedOutcome, setEditedOutcome] = useState(step.expected_outcome);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = () => {
    onUpdate(step.id, {
      task_description: editedDescription,
      expected_outcome: editedOutcome,
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedDescription(step.task_description);
    setEditedOutcome(step.expected_outcome);
    setIsEditing(false);
  };

  const handleDelete = () => {
    onDelete(step.id);
    setShowDeleteConfirm(false);
  };

  // 📊 v7.360: 内联搜索状态
  const inlineSearch = step.inlineSearch;
  const isSearching = inlineSearch?.status === 'searching';
  const isCompleted = inlineSearch?.status === 'completed';
  const isFailed = inlineSearch?.status === 'failed';
  const sourcesCount = inlineSearch?.sources?.length || 0;
  const searchDuration = inlineSearch?.startTime && inlineSearch?.endTime
    ? ((inlineSearch.endTime - inlineSearch.startTime) / 1000).toFixed(1)
    : null;

  // 状态颜色
  const getStatusStyle = () => {
    if (isSearching) return 'border-blue-400 bg-blue-50/50';
    if (isCompleted) return 'border-green-400 bg-green-50/30';
    if (isFailed) return 'border-red-400 bg-red-50/30';
    if (isEditing) return 'border-blue-400 bg-blue-50/50 shadow-md';
    return 'border-gray-200 dark:border-gray-300 bg-white dark:bg-white hover:border-gray-300 dark:hover:border-gray-400';
  };

  return (
    <div
      className={`
        relative group rounded-lg border transition-all duration-200
        ${getStatusStyle()}
        ${step.status === 'complete' && !isCompleted ? 'opacity-75' : ''}
      `}
    >
      {/* 拖拽手柄 */}
      {showDragHandle && !isReadOnly && (
        <div className="absolute left-0 top-0 bottom-0 w-8 flex items-center justify-center cursor-grab opacity-0 group-hover:opacity-100 transition-opacity">
          <GripVertical className="w-4 h-4 text-gray-400" />
        </div>
      )}

      <div className={`p-4 ${showDragHandle ? 'pl-8' : ''}`}>
        {/* 用户添加/修改/动态增补标记 */}
        {(step.is_user_added || step.is_user_modified || step.is_supplementary) && (
          <div className="flex items-center gap-2 mb-2">
            {step.is_user_added && (
              <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs">
                新增
              </span>
            )}
            {step.is_user_modified && !step.is_user_added && (
              <span className="px-2 py-0.5 rounded bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 text-xs">
                已修改
              </span>
            )}
            {step.is_supplementary && (
              <span className="px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 text-xs">
                🔄 动态增补
              </span>
            )}
          </div>
        )}

        {/* 内容区域 */}
        {isEditing ? (
          <div className="space-y-3">
            {/* 任务描述编辑 */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-600 mb-1">
                搜索任务
              </label>
              <textarea
                ref={inputRef}
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-400 bg-white dark:bg-white text-sm text-gray-900 dark:text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
                placeholder="描述要搜索的内容..."
              />
            </div>

            {/* 期望结果编辑 */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-600 mb-1">
                期望结果
              </label>
              <textarea
                value={editedOutcome}
                onChange={(e) => setEditedOutcome(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-400 bg-white dark:bg-white text-sm text-gray-900 dark:text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
                placeholder="期望获得什么信息..."
              />
            </div>

            {/* 编辑模式操作按钮 */}
            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={handleSave}
                className="px-3 py-1.5 rounded bg-blue-500 hover:bg-blue-600 text-white text-sm transition-colors flex items-center gap-1"
              >
                <Check className="w-4 h-4" />
                保存
              </button>
              <button
                onClick={handleCancel}
                className="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-200 hover:bg-gray-300 dark:hover:bg-gray-300 text-gray-600 dark:text-gray-700 text-sm transition-colors flex items-center gap-1"
              >
                <X className="w-4 h-4" />
                取消
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 space-y-2">
                {/* 任务描述 */}
                <div className="flex items-start gap-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-100 text-gray-700 dark:text-gray-700 text-xs font-medium flex-shrink-0 mt-0.5">
                    搜索{displayIndex ?? step.step_number}
                  </span>
                  <p className="text-sm text-gray-900 dark:text-gray-900 leading-relaxed font-medium flex-1">
                    {step.task_description}
                  </p>
                </div>

                {/* 搜索关键词 */}
                {step.search_keywords && step.search_keywords.length > 0 && (
                  <div className="flex flex-wrap gap-1 pl-6 mt-2">
                    {step.search_keywords.map((keyword, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-100 text-xs text-gray-600 dark:text-gray-600"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* 操作按钮 - 右侧 */}
              {!isReadOnly && !isSearching && !isCompleted && (
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                  <button
                    onClick={() => setIsEditing(true)}
                    className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-100 text-gray-500 hover:text-blue-500 transition-colors"
                    title="编辑"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-100 text-gray-500 hover:text-red-500 transition-colors"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* 📊 v7.460: 搜索状态指示器（增强版，显示轮次进度） */}
              {/* v7.500: 更新为显示自主搜索进度 */}
              {isSearching && (
                <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-xs">
                    深入搜索中... (第 {(inlineSearch?.rounds?.filter(r => r.status === 'complete').length || 0) + 1} 次尝试)
                  </span>
                </div>
              )}
              {isCompleted && (
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span className="text-xs">
                    {sourcesCount} 条高质量结果
                  </span>
                  {searchDuration && (
                    <span className="text-xs text-gray-500 dark:text-gray-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {searchDuration}s
                    </span>
                  )}
                </div>
              )}
              {isFailed && (
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-xs">搜索失败</span>
                </div>
              )}
            </div>

            {/* 📊 v7.500: 可折叠搜索结果（沉淀结果视图） */}
            {(isSearching || isCompleted) && (inlineSearch?.rounds?.length || 0) > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-300">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                >
                  {showSources ? '收起结果' : `查看 ${sourcesCount} 条搜索结果`}
                </button>
                {showSources && (
                  <div className="mt-2 space-y-1">
                    {inlineSearch?.sources?.map((source, sIdx) => (
                      <a
                        key={sIdx}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[11px] text-blue-600 dark:text-blue-400 hover:underline truncate"
                      >
                        <ExternalLink className="w-3 h-3 flex-shrink-0" />
                        {source.title || source.url}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* v7.460: 仅在无轮次数据时显示旧版扁平来源列表（向后兼容） */}
            {isCompleted && sourcesCount > 0 && !(inlineSearch?.rounds?.length) && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-300">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                >
                  {showSources ? '收起结果' : `查看 ${sourcesCount} 条搜索结果`}
                </button>
                {showSources && (
                  <div className="mt-2 space-y-2">
                    {inlineSearch?.sources?.map((source, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-gray-50 dark:bg-gray-50 border border-gray-100 dark:border-gray-200"
                      >
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                        >
                          {source.title}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                        {source.snippet && (
                          <p className="text-xs text-gray-600 dark:text-gray-600 mt-1 line-clamp-2">
                            {source.snippet}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 搜索失败错误信息 */}
            {isFailed && inlineSearch?.error && (
              <div className="mt-3 pt-3 border-t border-red-200 dark:border-red-800">
                <p className="text-xs text-red-600 dark:text-red-400">
                  错误: {inlineSearch.error}
                </p>
              </div>
            )}
          </div>
        )}

        {/* 删除确认对话框 */}
        {showDeleteConfirm && (
          <div className="absolute inset-0 bg-white/95 dark:bg-white/95 rounded-lg flex items-center justify-center z-10">
            <div className="text-center">
              <p className="text-sm text-gray-600 dark:text-gray-700 mb-3">
                确定删除这个搜索步骤吗？
              </p>
              <div className="flex items-center justify-center gap-2">
                <button
                  onClick={handleDelete}
                  className="px-3 py-1.5 rounded bg-red-500 hover:bg-red-600 text-white text-sm transition-colors"
                >
                  删除
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-200 hover:bg-gray-300 dark:hover:bg-gray-300 text-gray-600 dark:text-gray-700 text-sm transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EditableSearchStepCard;
