// components/ConfirmationModal.tsx
// 需求确认 Modal 组件

'use client';

import { useState, useEffect } from 'react';
import { CheckCircle2, Edit2, Save, X } from 'lucide-react';

interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  summary?: any;
  onConfirm: (editedData?: any) => void;
  onEdit?: () => void;
}

export function ConfirmationModal({
  isOpen,
  title,
  message,
  summary,
  onConfirm,
  onEdit
}: ConfirmationModalProps) {
  const [editedItems, setEditedItems] = useState<any[]>([]);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (isOpen && summary) {
      // 处理数组格式的数据
      if (Array.isArray(summary)) {
        setEditedItems(JSON.parse(JSON.stringify(summary)));
      } else if (typeof summary === 'object') {
        // 尝试找到数组数据
        const firstValue = Object.values(summary)[0];
        if (Array.isArray(firstValue)) {
          setEditedItems(JSON.parse(JSON.stringify(firstValue)));
        } else {
          // 转换为数组格式
          setEditedItems([summary]);
        }
      }
    }
  }, [isOpen, summary]);

  if (!isOpen) return null;

  const handleEdit = (index: number, field: string, value: string) => {
    const newItems = [...editedItems];
    newItems[index] = { ...newItems[index], [field]: value };
    setEditedItems(newItems);
  };

  const handleConfirm = () => {
    if (isEditing) {
      // 保存编辑后的数据
      onConfirm(editedItems);
    } else {
      onConfirm();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white dark:bg-[var(--card-bg)] rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-gray-200 dark:border-[var(--border-color)]">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-[var(--border-color)] px-6 py-5 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{message}</p>
            </div>
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
              >
                <Edit2 className="w-4 h-4" />
                <span>修改需求</span>
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="space-y-4">
            {editedItems.map((item, index) => (
              <div
                key={index}
                className="bg-gray-50 dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700 rounded-lg p-5"
              >
                {/* 标题行 */}
                <div className="flex items-start gap-3 mb-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-gray-200 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-400 flex items-center justify-center text-sm font-medium mt-0.5">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    {isEditing ? (
                      <input
                        type="text"
                        value={item.label || ''}
                        onChange={(e) => handleEdit(index, 'label', e.target.value)}
                        className="w-full px-3 py-2 text-base font-medium text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
                        placeholder="输入标题..."
                      />
                    ) : (
                      <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">{item.label}</h3>
                    )}
                  </div>
                </div>

                {/* 内容区域 */}
                <div className="ml-9">
                  {isEditing ? (
                    <textarea
                      value={item.content || ''}
                      onChange={(e) => handleEdit(index, 'content', e.target.value)}
                      className="w-full px-3 py-2 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none min-h-[100px] leading-relaxed resize-y"
                      placeholder="输入详细内容..."
                    />
                  ) : (
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                      {item.content}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* 编辑提示 */}
          {isEditing && (
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                编辑模式：您可以修改标题和内容，点击"保存并继续"提交修改。
              </p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-200 dark:border-[var(--border-color)] px-6 py-4 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-end gap-3">
          {isEditing ? (
            <>
              <button
                onClick={() => {
                  setIsEditing(false);
                  // 重置数据
                  if (Array.isArray(summary)) {
                    setEditedItems(JSON.parse(JSON.stringify(summary)));
                  }
                }}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
              >
                取消
              </button>
              <button
                onClick={() => {
                  setIsEditing(false);
                  handleConfirm();
                }}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
              >
                保存并继续
              </button>
            </>
          ) : (
            <button
              onClick={handleConfirm}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
            >
              确认继续
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
