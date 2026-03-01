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
    <div className={`ucppt-card ${className}`}>
      {/* 卡片头部 */}
      <div className="ucppt-card-header ucppt-card-header-expanded">
        <div className="flex items-center gap-3">
          <div className="ucppt-icon-circle ucppt-icon-blue">
            <MessageCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <span className="ucppt-title-blue">用户问题</span>
        </div>
      </div>

      {/* 卡片内容 - 分割线后的内容区域 */}
      <div className="ucppt-card-content">
        <p
          className="text-sm leading-relaxed whitespace-pre-wrap break-words"
          style={{ color: 'rgb(17, 24, 39)' }}
        >
          {question}
        </p>
      </div>
    </div>
  );
}
