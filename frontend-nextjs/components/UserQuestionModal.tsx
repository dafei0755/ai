// components/UserQuestionModal.tsx
// 完成后追问交互的 Modal 组件

'use client';

import { useEffect, useState } from 'react';
import { Loader2, MessageCircle, Send, Sparkles, X } from 'lucide-react';

interface UserQuestionData {
  message: string;
  placeholder?: string;
  current_analysis?: {
    completed_sections?: string[];
    available_topics?: string[];
  };
}

interface UserQuestionModalProps {
  isOpen: boolean;
  data: UserQuestionData | null;
  onSubmit: (payload: { question: string; requiresAnalysis: boolean }) => void;
  onSkip: () => void;
  submitting?: boolean;
}

export function UserQuestionModal({
  isOpen,
  data,
  onSubmit,
  onSkip,
  submitting = false,
}: UserQuestionModalProps) {
  const [question, setQuestion] = useState('');
  const [requiresAnalysis, setRequiresAnalysis] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setQuestion('');
      setRequiresAnalysis(true);
    }
  }, [isOpen]);

  if (!isOpen || !data) {
    return null;
  }

  const handleSubmit = () => {
    if (!canSubmit || submitting) {
      return;
    }
    onSubmit({ question: question.trim(), requiresAnalysis });
  };

  const canSubmit = question.trim().length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-xl bg-white dark:bg-[var(--card-bg)] shadow-2xl border border-gray-200 dark:border-[var(--border-color)]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-[var(--border-color)] px-6 py-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 dark:bg-indigo-500 text-white shadow-lg">
              <MessageCircle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">后续追问</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">报告已经生成，欢迎继续深入探讨</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              if (!submitting) {
                onSkip();
              }
            }}
            className={`transition ${submitting ? 'cursor-not-allowed text-gray-300 dark:text-gray-600' : 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'}`}
            aria-label="关闭追问"
            disabled={submitting}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 px-6 py-5 bg-gray-50/50 dark:bg-transparent">
          {/* Intro message */}
          <div className="rounded-lg bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-100 dark:border-indigo-800 p-4 text-sm text-indigo-800 dark:text-indigo-200">
            {data.message || '有什么想进一步了解的吗？'}
          </div>

          {/* Context */}
          {(data.current_analysis?.completed_sections?.length || data.current_analysis?.available_topics?.length) && (
            <div className="grid gap-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4 sm:grid-cols-2">
              {data.current_analysis?.completed_sections?.length ? (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                    <Sparkles className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
                    已完成的分析章节
                  </div>
                  <ul className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    {data.current_analysis.completed_sections.map((section) => (
                      <li key={section}>• {section}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {data.current_analysis?.available_topics?.length ? (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                    <Sparkles className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
                    推荐深入话题
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {data.current_analysis.available_topics.map((topic) => (
                      <button
                        key={topic}
                        type="button"
                        onClick={() => setQuestion(topic)}
                        className="rounded-full bg-white dark:bg-gray-700 px-3 py-1 text-xs text-indigo-600 dark:text-indigo-300 shadow-sm ring-1 ring-indigo-200 dark:ring-indigo-700 transition hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
                      >
                        {topic}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* Question input */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">您的问题</label>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={5}
              placeholder={data.placeholder || '请输入想深入了解的问题或要点'}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-3 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <div className="mt-3 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <input
                id="requires-analysis-checkbox"
                type="checkbox"
                checked={requiresAnalysis}
                onChange={(event) => setRequiresAnalysis(event.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="requires-analysis-checkbox">
                需要智能体继续分析（取消勾选表示只是简单反馈或无需进一步处理）
              </label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-gray-200 dark:border-[var(--border-color)] bg-gray-50 dark:bg-[var(--sidebar-bg)] px-6 py-4">
          <button
            type="button"
            onClick={onSkip}
            disabled={submitting}
            className={`text-sm font-medium transition ${
              submitting
                ? 'cursor-not-allowed text-gray-400 dark:text-gray-600'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            暂时没有问题
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${
              !canSubmit || submitting
                ? 'cursor-not-allowed bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-500'
                : 'bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-700 text-white shadow'
            }`}
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span>{requiresAnalysis ? '提交追问' : '发送反馈'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
