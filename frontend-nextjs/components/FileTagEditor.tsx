// components/FileTagEditor.tsx
// v7.157: 文件标签编辑器组件 - 支持图片/文档的标签选择和自定义描述

'use client';

import { useState, useEffect } from 'react';
import {
  X,
  Palette,
  Sparkles,
  Layers,
  Layout,
  Mountain,
  Heart,
  Armchair,
  Sun,
  FileText,
  BookOpen,
  ClipboardList,
  Calculator,
  FileSignature,
  File,
  Image as ImageIcon
} from 'lucide-react';
import type { ImageCategory, DocumentCategory, UploadedFileMetadata } from '@/types';

// 图片分类配置
const IMAGE_CATEGORIES: Array<{
  id: ImageCategory;
  label: string;
  icon: React.ReactNode;
  color: string;
}> = [
  { id: 'color', label: '色彩参考', icon: <Palette className="w-4 h-4" />, color: '#F59E0B' },
  { id: 'style', label: '风格参考', icon: <Sparkles className="w-4 h-4" />, color: '#8B5CF6' },
  { id: 'material', label: '材质参考', icon: <Layers className="w-4 h-4" />, color: '#6B7280' },
  { id: 'layout', label: '平面布局', icon: <Layout className="w-4 h-4" />, color: '#3B82F6' },
  { id: 'environment', label: '环境参考', icon: <Mountain className="w-4 h-4" />, color: '#10B981' },
  { id: 'mood', label: '格调参考', icon: <Heart className="w-4 h-4" />, color: '#EC4899' },
  { id: 'item', label: '单品参考', icon: <Armchair className="w-4 h-4" />, color: '#F97316' },
  { id: 'lighting', label: '光线参考', icon: <Sun className="w-4 h-4" />, color: '#FBBF24' },
];

// 文档分类配置
const DOCUMENT_CATEGORIES: Array<{
  id: DocumentCategory;
  label: string;
  icon: React.ReactNode;
  color: string;
}> = [
  { id: 'requirements', label: '需求文档', icon: <FileText className="w-4 h-4" />, color: '#3B82F6' },
  { id: 'reference', label: '参考资料', icon: <BookOpen className="w-4 h-4" />, color: '#8B5CF6' },
  { id: 'specification', label: '技术规范', icon: <ClipboardList className="w-4 h-4" />, color: '#6B7280' },
  { id: 'budget', label: '预算清单', icon: <Calculator className="w-4 h-4" />, color: '#10B981' },
  { id: 'contract', label: '合同协议', icon: <FileSignature className="w-4 h-4" />, color: '#EF4444' },
  { id: 'other', label: '其他', icon: <File className="w-4 h-4" />, color: '#9CA3AF' },
];

interface FileTagEditorProps {
  fileMetadata: UploadedFileMetadata;
  onUpdate: (updated: UploadedFileMetadata) => void;
  onRemove: () => void;
  disabled?: boolean;
}

export function FileTagEditor({
  fileMetadata,
  onUpdate,
  onRemove,
  disabled = false
}: FileTagEditorProps) {
  const { file, categories, customDescription, previewUrl, isImage } = fileMetadata;
  const categoryConfig = isImage ? IMAGE_CATEGORIES : DOCUMENT_CATEGORIES;

  // 切换标签选中状态
  const toggleCategory = (categoryId: string) => {
    if (disabled) return;

    const currentCategories = categories as string[];
    const isSelected = currentCategories.includes(categoryId);

    let newCategories: string[];
    if (isSelected) {
      newCategories = currentCategories.filter(c => c !== categoryId);
    } else {
      newCategories = [...currentCategories, categoryId];
    }

    onUpdate({
      ...fileMetadata,
      categories: newCategories as ImageCategory[] | DocumentCategory[]
    });
  };

  // 更新自定义描述
  const updateDescription = (value: string) => {
    if (disabled) return;
    onUpdate({
      ...fileMetadata,
      customDescription: value
    });
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 space-y-3 transition-all hover:shadow-md">
      {/* 文件头部：预览 + 文件名 + 删除按钮 */}
      <div className="flex items-start gap-3">
        {/* 缩略图/图标 */}
        <div className="flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
          {isImage && previewUrl ? (
            <img
              src={previewUrl}
              alt={file.name}
              className="w-full h-full object-cover"
            />
          ) : isImage ? (
            <ImageIcon className="w-8 h-8 text-gray-400" />
          ) : (
            <FileText className="w-8 h-8 text-gray-400" />
          )}
        </div>

        {/* 文件信息 */}
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {file.name}
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {formatFileSize(file.size)}
            {isImage ? ' · 图片' : ' · 文档'}
          </p>

          {/* 已选标签预览 */}
          {categories.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {(categories as string[]).map(catId => {
                const cat = categoryConfig.find(c => c.id === catId);
                if (!cat) return null;
                return (
                  <span
                    key={catId}
                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs rounded-full"
                    style={{ backgroundColor: `${cat.color}20`, color: cat.color }}
                  >
                    {cat.icon}
                    <span className="ml-0.5">{cat.label}</span>
                  </span>
                );
              })}
            </div>
          )}
        </div>

        {/* 删除按钮 */}
        <button
          type="button"
          onClick={onRemove}
          disabled={disabled}
          className="flex-shrink-0 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
          title="删除文件"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 标签选择区域 */}
      <div className="space-y-2">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          选择{isImage ? '参考类型' : '文档类型'}（可多选）：
        </p>
        <div className="flex flex-wrap gap-2">
          {categoryConfig.map(cat => {
            const isSelected = (categories as string[]).includes(cat.id);
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => toggleCategory(cat.id)}
                disabled={disabled}
                className={`
                  inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg
                  border transition-all duration-200
                  ${isSelected
                    ? 'border-transparent text-white shadow-sm'
                    : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
                style={isSelected ? { backgroundColor: cat.color } : undefined}
              >
                {cat.icon}
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 自定义描述输入 */}
      <div className="space-y-1.5">
        <label className="text-xs text-gray-500 dark:text-gray-400">
          补充说明（可选）：
        </label>
        <input
          type="text"
          value={customDescription}
          onChange={(e) => updateDescription(e.target.value)}
          placeholder={isImage ? '例如：希望参考这张图的色彩搭配...' : '例如：这是项目的详细需求说明...'}
          disabled={disabled}
          className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg
            bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
            placeholder:text-gray-400 dark:placeholder:text-gray-500
            focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed"
        />
      </div>
    </div>
  );
}

export { IMAGE_CATEGORIES, DOCUMENT_CATEGORIES };
