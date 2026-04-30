// components/report/QuestionnaireSection.tsx
// 🔥 Phase 1.4+ P3: 问卷回答显示组件

'use client';

import { FileQuestion } from 'lucide-react';

interface QuestionnaireResponseItem {
  question_id: string;
  question: string;
  answer: string;
  context: string;
}

interface QuestionnaireResponseData {
  responses: QuestionnaireResponseItem[];
  timestamp: string;
  analysis_insights?: string;  // 🔥 修复: 改为可选字段
  notes?: string;  // 🔥 新增: 支持 notes 字段
}

interface QuestionnaireSectionProps {
  questionnaireData: QuestionnaireResponseData | null | undefined;
}

export default function QuestionnaireSection({ questionnaireData }: QuestionnaireSectionProps) {
  if (!questionnaireData || !questionnaireData.responses || questionnaireData.responses.length === 0) {
    return null; // 用户跳过问卷
  }

  return (
    <div id="questionnaire-responses" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
          <FileQuestion className="w-5 h-5 text-purple-400" />
        </div>
        <h2 className="text-lg font-semibold text-white">问卷回顾</h2>
      </div>

      {/* 🔥 横向3列网格布局 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {questionnaireData.responses.map((item, idx) => (
          <div key={item.question_id || idx} className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col h-full">
            {/* 问题编号和标题 - 上下布局 */}
            <div className="mb-3">
              <div className="w-7 h-7 rounded-full bg-purple-500/30 flex items-center justify-center text-sm font-bold text-purple-400 mb-2">
                Q{idx + 1}
              </div>
              <div>
                {/* 问题背景在第一行（灰色+冒号），问题在第二行 */}
                {item.context && (
                  <p className="text-sm text-gray-500 leading-relaxed mb-1">{item.context}:</p>
                )}
                <p className="text-sm text-gray-200 font-medium leading-relaxed">{item.question}</p>
              </div>
            </div>

            {/* 回答内容 - 固定在卡片底部 */}
            <div className="mt-auto pt-3">
              <div className="text-xs text-gray-400 mb-1.5">您的回答</div>
              <div className="text-white bg-purple-500/10 px-3 py-2 rounded border border-purple-500/30 text-sm">
                {/* 处理多选答案：移除"选项N: "前缀，多个答案换行显示 */}
                {item.answer.includes('选项') ? (
                  <div className="space-y-1">
                    {item.answer.split(/[,，、]/).map((ans, i) => {
                      const cleanAns = ans.replace(/选项[A-Z\d]+[:：]\s*/g, '').trim();
                      return cleanAns ? <div key={i}>{cleanAns}</div> : null;
                    })}
                  </div>
                ) : (
                  item.answer
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
