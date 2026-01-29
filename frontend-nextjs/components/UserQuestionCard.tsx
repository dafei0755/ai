/**
 * 用户问题卡片组件
 * v7.290: 统一搜索模式和分析模式的用户问题显示
 *
 * @description
 * 显示用户最初提出的问题，支持多行文本和自动换行
 * 在错误页面或正常流程中都能显示，提供一致的用户体验
 */

import { MessageCircle } from 'lucide-react';

interface UserQuestionCardProps {
  /** 用户输入的问题内容 */
  question: string;
  /** 可选的自定义类名 */
  className?: string;
}

export function UserQuestionCard({ question, className = '' }: UserQuestionCardProps) {
  if (!question) return null;

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-200 dark:border-gray-700 ${className}`}>
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
          <MessageCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-1">用户问题</p>
          <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap break-words">
            {question}
          </p>
        </div>
      </div>
    </div>
  );
}
