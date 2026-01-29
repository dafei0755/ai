'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Edit3,
  Trash2,
  Check,
  X,
  GripVertical,
  Search,
  ChevronRight,
  Loader2,
  CheckCircle,
  Circle,
  Zap,
} from 'lucide-react';
import type { EditableSearchStep } from '@/types';

interface EditableSearchStepCardProps {
  step: EditableSearchStep;
  onUpdate: (stepId: string, updates: Partial<EditableSearchStep>) => void;
  onDelete: (stepId: string) => void;
  isReadOnly?: boolean;
  showDragHandle?: boolean;
}

/**
 * v7.300: 可编辑的搜索步骤卡片
 *
 * 功能：
 * - 点击编辑任务描述和期望结果
 * - 删除步骤
 * - 显示优先级和并行状态
 * - 显示执行状态（pending/searching/complete）
 */
const EditableSearchStepCard: React.FC<EditableSearchStepCardProps> = ({
  step,
  onUpdate,
  onDelete,
  isReadOnly = false,
  showDragHandle = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedDescription, setEditedDescription] = useState(step.task_description);
  const [editedOutcome, setEditedOutcome] = useState(step.expected_outcome);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
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

  // 优先级颜色
  const priorityColors = {
    high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    low: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  };

  // 状态图标
  const StatusIcon = () => {
    switch (step.status) {
      case 'searching':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      default:
        return <Circle className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div
      className={`
        relative group rounded-lg border transition-all duration-200
        ${isEditing
          ? 'border-blue-400 bg-blue-50/50 dark:bg-blue-900/10 shadow-md'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
        }
        ${step.status === 'complete' ? 'opacity-75' : ''}
      `}
    >
      {/* 拖拽手柄 */}
      {showDragHandle && !isReadOnly && (
        <div className="absolute left-0 top-0 bottom-0 w-8 flex items-center justify-center cursor-grab opacity-0 group-hover:opacity-100 transition-opacity">
          <GripVertical className="w-4 h-4 text-gray-400" />
        </div>
      )}

      <div className={`p-4 ${showDragHandle ? 'pl-8' : ''}`}>
        {/* 头部：步骤编号 + 状态 + 操作按钮 */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {/* 步骤编号 */}
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-medium">
              {step.step_number}
            </span>

            {/* 状态图标 */}
            <StatusIcon />

            {/* 优先级标签 */}
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${priorityColors[step.priority]}`}>
              {step.priority === 'high' ? '高优' : step.priority === 'medium' ? '中优' : '低优'}
            </span>

            {/* 并行标记 */}
            {step.can_parallel && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 text-xs">
                <Zap className="w-3 h-3" />
                可并行
              </span>
            )}

            {/* 用户添加/修改标记 */}
            {step.is_user_added && (
              <span className="px-2 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-xs">
                新增
              </span>
            )}
            {step.is_user_modified && !step.is_user_added && (
              <span className="px-2 py-0.5 rounded bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 text-xs">
                已修改
              </span>
            )}
          </div>

          {/* 操作按钮 */}
          {!isReadOnly && !isEditing && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => setIsEditing(true)}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 hover:text-blue-500 transition-colors"
                title="编辑"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 hover:text-red-500 transition-colors"
                title="删除"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* 编辑模式操作按钮 */}
          {isEditing && (
            <div className="flex items-center gap-1">
              <button
                onClick={handleSave}
                className="p-1.5 rounded bg-blue-500 hover:bg-blue-600 text-white transition-colors"
                title="保存"
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                onClick={handleCancel}
                className="p-1.5 rounded bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 transition-colors"
                title="取消"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* 内容区域 */}
        {isEditing ? (
          <div className="space-y-3">
            {/* 任务描述编辑 */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                搜索任务
              </label>
              <textarea
                ref={inputRef}
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
                placeholder="描述要搜索的内容..."
              />
            </div>

            {/* 期望结果编辑 */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                期望结果
              </label>
              <textarea
                value={editedOutcome}
                onChange={(e) => setEditedOutcome(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
                placeholder="期望获得什么信息..."
              />
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {/* 任务描述 */}
            <div className="flex items-start gap-2">
              <Search className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
                {step.task_description}
              </p>
            </div>

            {/* 期望结果 */}
            {step.expected_outcome && (
              <div className="flex items-start gap-2 pl-6">
                <ChevronRight className="w-3 h-3 text-gray-400 mt-1 flex-shrink-0" />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  期望：{step.expected_outcome}
                </p>
              </div>
            )}

            {/* 搜索关键词 */}
            {step.search_keywords && step.search_keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 pl-6 mt-2">
                {step.search_keywords.map((keyword, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-xs text-gray-600 dark:text-gray-300"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 删除确认对话框 */}
        {showDeleteConfirm && (
          <div className="absolute inset-0 bg-white/95 dark:bg-gray-800/95 rounded-lg flex items-center justify-center z-10">
            <div className="text-center">
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
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
                  className="px-3 py-1.5 rounded bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 text-sm transition-colors"
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
