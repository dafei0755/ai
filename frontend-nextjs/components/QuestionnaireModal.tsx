// components/QuestionnaireModal.tsx
// 校准问卷 Modal 组件

'use client';

import { useState } from 'react';
import { Send, SkipForward } from 'lucide-react';

interface Question {
  id?: string;  // 问题ID
  question: string;
  context: string;
  type: 'single_choice' | 'multiple_choice' | 'open_ended';
  options?: string[];
}

interface Questionnaire {
  introduction: string;
  questions: Question[];
  note: string;
}

interface QuestionnaireModalProps {
  isOpen: boolean;
  questionnaire: Questionnaire | null;
  onSubmit: (answers: Record<string, any>) => void;
  onSkip: () => void;
}

export function QuestionnaireModal({
  isOpen,
  questionnaire,
  onSubmit,
  onSkip
}: QuestionnaireModalProps) {
  const [answers, setAnswers] = useState<Record<string, any>>({});

  if (!isOpen || !questionnaire) return null;

  const handleSingleChoice = (index: number, value: string) => {
    setAnswers(prev => ({ ...prev, [index]: value }));
  };

  const handleMultipleChoice = (index: number, value: string) => {
    setAnswers(prev => {
      const current = prev[index] || [];
      const updated = current.includes(value)
        ? current.filter((v: string) => v !== value)
        : [...current, value];
      return { ...prev, [index]: updated };
    });
  };

  const handleOpenEnded = (index: number, value: string) => {
    setAnswers(prev => ({ ...prev, [index]: value }));
  };

  const handleSubmit = () => {
    // 转换为后端期望的格式（包含 question_id）
    const formattedAnswers = questionnaire.questions.map((q, i) => ({
      question_id: q.id || `Q${i + 1}`,  // 使用问题ID或生成默认ID
      question: q.question,
      answer: answers[i] || (q.type === 'multiple_choice' ? [] : ''),
      type: q.type,
      context: q.context || ''
    }));
    onSubmit(formattedAnswers);
  };

  const isAnswerComplete = (index: number, type: string) => {
    const answer = answers[index];
    if (type === 'open_ended') return answer && answer.trim().length > 0;
    if (type === 'multiple_choice') return Array.isArray(answer) && answer.length > 0;
    return !!answer;
  };

  const allAnswered = questionnaire.questions.every((q, i) => 
    isAnswerComplete(i, q.type)
  );

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">战略校准问卷</h2>
            <p className="text-sm text-gray-500 mt-1">
              {questionnaire.questions.length} 个问题 •
              已回答 {Object.keys(answers).length} 个
            </p>
          </div>
        </div>

        {/* Introduction */}
        <div className="px-6 py-4 bg-blue-50 border-b">
          <p className="text-sm text-gray-700">{questionnaire.introduction}</p>
        </div>

        {/* Questions */}
        <div className="px-6 py-4 space-y-6">
          {questionnaire.questions.map((q, index) => (
            <div key={index} className="border rounded-lg p-4">
              {/* Question Title */}
              <div className="mb-3">
                <div className="flex items-start gap-2">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-medium">
                    {index + 1}
                  </span>
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{q.question}</h3>
                    <p className="text-xs text-gray-500 mt-1">{q.context}</p>
                  </div>
                  {isAnswerComplete(index, q.type) && (
                    <span className="text-green-500">✓</span>
                  )}
                </div>
              </div>

              {/* Answer Options */}
              {q.type === 'single_choice' && q.options && (
                <div className="space-y-2 ml-8">
                  {q.options.map((option, optIndex) => (
                    <label
                      key={optIndex}
                      className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition"
                    >
                      <input
                        type="radio"
                        name={`question_${index}`}
                        value={option}
                        checked={answers[index] === option}
                        onChange={(e) => handleSingleChoice(index, e.target.value)}
                        className="w-4 h-4 text-blue-600"
                      />
                      <span className="text-sm text-gray-700">{option}</span>
                    </label>
                  ))}
                </div>
              )}

              {q.type === 'multiple_choice' && q.options && (
                <div className="space-y-2 ml-8">
                  {q.options.map((option, optIndex) => (
                    <label
                      key={optIndex}
                      className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition"
                    >
                      <input
                        type="checkbox"
                        value={option}
                        checked={(answers[index] || []).includes(option)}
                        onChange={(e) => handleMultipleChoice(index, e.target.value)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <span className="text-sm text-gray-700">{option}</span>
                    </label>
                  ))}
                </div>
              )}

              {q.type === 'open_ended' && (
                <div className="ml-8">
                  <textarea
                    value={answers[index] || ''}
                    onChange={(e) => handleOpenEnded(index, e.target.value)}
                    placeholder="请输入您的回答..."
                    rows={4}
                    className="w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-gray-900 placeholder:text-gray-400"
                  />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Note */}
        {questionnaire.note && (
          <div className="px-6 py-3 bg-gray-50 border-t">
            <p className="text-xs text-gray-500">{questionnaire.note}</p>
          </div>
        )}

        {/* Footer Actions */}
        <div className="sticky bottom-0 bg-white border-t px-6 py-4 flex items-center justify-between">
          <button
            onClick={onSkip}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition"
          >
            <SkipForward className="w-4 h-4" />
            <span>跳过问卷</span>
          </button>

          <button
            onClick={handleSubmit}
            disabled={!allAnswered}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition ${
              allAnswered
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            <Send className="w-4 h-4" />
            <span>提交问卷</span>
          </button>
        </div>
      </div>
    </div>
  );
}
