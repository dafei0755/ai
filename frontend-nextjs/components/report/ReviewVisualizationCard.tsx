// components/report/ReviewVisualizationCard.tsx
// 审核可视化卡片组件

'use client';

import { FC, useState } from 'react';
import { Shield, ChevronDown, ChevronUp, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { ReviewFeedback, ReviewVisualization } from '@/types';

interface ReviewVisualizationCardProps {
  reviewFeedback?: ReviewFeedback | null;
  reviewVisualization?: ReviewVisualization | null;
}

const ReviewVisualizationCard: FC<ReviewVisualizationCardProps> = ({
  reviewFeedback,
  reviewVisualization,
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  if (!reviewFeedback && !reviewVisualization) return null;

  // 格式化迭代总结（处理 Markdown）
  const formatIterationSummary = (text: string) => {
    if (!text) return null;
    
    // 移除转义的换行符，替换为实际换行
    let cleaned = text
      .replace(/\\n/g, '\n')
      .replace(/\*\*/g, '')  // 移除 **粗体** 标记
      .replace(/\*/g, '')    // 移除 *斜体* 标记
      .trim();
    
    // 按换行分割成行
    const lines = cleaned.split('\n').filter(line => line.trim());
    
    return lines.map((line, index) => {
      const trimmedLine = line.trim();
      
      // 处理标题 (## 或 ###)
      if (trimmedLine.startsWith('### ')) {
        return (
          <h4 key={index} className="text-base font-semibold text-white mt-3 mb-1">
            {trimmedLine.replace('### ', '')}
          </h4>
        );
      }
      if (trimmedLine.startsWith('## ')) {
        return (
          <h3 key={index} className="text-lg font-semibold text-white mt-4 mb-2">
            {trimmedLine.replace('## ', '')}
          </h3>
        );
      }
      
      // 处理列表项 (- 开头)
      if (trimmedLine.startsWith('- ')) {
        return (
          <div key={index} className="flex items-start gap-2 my-1">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>{trimmedLine.substring(2)}</span>
          </div>
        );
      }
      
      // 普通段落
      return (
        <p key={index} className="my-1">{trimmedLine}</p>
      );
    });
  };

  // 决策状态颜色
  const getDecisionColor = (decision: string) => {
    if (decision.includes('通过') && !decision.includes('条件')) {
      return { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20' };
    }
    if (decision.includes('条件')) {
      return { icon: AlertCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
    }
    return { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/20' };
  };

  // 优先级颜色
  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'bg-red-500/20 text-red-400';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'low':
        return 'bg-green-500/20 text-green-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  const decisionInfo = reviewVisualization?.final_decision
    ? getDecisionColor(reviewVisualization.final_decision)
    : null;

  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl overflow-hidden">
      {/* 标题 */}
      <div className="px-6 py-4 border-b border-[var(--border-color)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">审核反馈</h2>
            <p className="text-sm text-gray-400">红蓝对抗审核结果</p>
          </div>
        </div>
        
        {/* 最终决策标签 */}
        {decisionInfo && reviewVisualization && (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${decisionInfo.bg}`}>
            <decisionInfo.icon className={`w-4 h-4 ${decisionInfo.color}`} />
            <span className={`text-sm font-medium ${decisionInfo.color}`}>
              {reviewVisualization.final_decision}
            </span>
          </div>
        )}
      </div>

      {/* 审核统计 */}
      {reviewVisualization && (
        <div className="px-6 py-4 border-b border-[var(--border-color)] bg-[var(--sidebar-bg)]/50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {reviewVisualization.total_rounds === 1 ? '✓' : reviewVisualization.total_rounds}
              </div>
              <div className="text-xs text-gray-400">
                {reviewVisualization.total_rounds === 1 ? '一次性审核' : `${reviewVisualization.total_rounds}轮审核`}
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">
                {Math.round(reviewVisualization.improvement_rate * 100)}%
              </div>
              <div className="text-xs text-gray-400">改进采纳率</div>
            </div>
            {reviewVisualization.rounds.length > 0 && (
              <>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-400">
                    {reviewVisualization.rounds[reviewVisualization.rounds.length - 1]?.red_score || 0}
                  </div>
                  <div className="text-xs text-gray-400">红队评分</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-400">
                    {reviewVisualization.rounds[reviewVisualization.rounds.length - 1]?.blue_score || 0}
                  </div>
                  <div className="text-xs text-gray-400">蓝队评分</div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* 反馈详情 */}
      {reviewFeedback && (
        <div className="divide-y divide-[var(--border-color)]">
          {/* 红队质疑 */}
          {reviewFeedback.red_team_challenges && reviewFeedback.red_team_challenges.length > 0 && (
            <div>
              <button
                onClick={() => setExpandedSection(expandedSection === 'red' ? null : 'red')}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-[var(--sidebar-bg)] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <span className="text-sm font-medium text-white">红队质疑</span>
                  <span className="text-xs text-gray-500">({reviewFeedback.red_team_challenges.length})</span>
                </div>
                {expandedSection === 'red' ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </button>
              {expandedSection === 'red' && (
                <div className="px-6 pb-4 space-y-3">
                  {reviewFeedback.red_team_challenges.map((item, index) => (
                    <div key={index} className="bg-[var(--sidebar-bg)] rounded-lg p-3 border border-red-500/20">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className="text-sm font-medium text-red-400">{item.issue_id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getPriorityColor(item.priority)}`}>
                          {item.priority}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 mb-2">{item.description}</p>
                      {item.response && (
                        <p className="text-xs text-gray-400 border-t border-[var(--border-color)] pt-2 mt-2">
                          <span className="text-green-400">响应：</span>{item.response}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 蓝队验证 */}
          {reviewFeedback.blue_team_validations && reviewFeedback.blue_team_validations.length > 0 && (
            <div>
              <button
                onClick={() => setExpandedSection(expandedSection === 'blue' ? null : 'blue')}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-[var(--sidebar-bg)] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-blue-400" />
                  <span className="text-sm font-medium text-white">蓝队验证</span>
                  <span className="text-xs text-gray-500">({reviewFeedback.blue_team_validations.length})</span>
                </div>
                {expandedSection === 'blue' ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </button>
              {expandedSection === 'blue' && (
                <div className="px-6 pb-4 space-y-3">
                  {reviewFeedback.blue_team_validations.map((item, index) => (
                    <div key={index} className="bg-[var(--sidebar-bg)] rounded-lg p-3 border border-blue-500/20">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className="text-sm font-medium text-blue-400">{item.issue_id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getPriorityColor(item.priority)}`}>
                          {item.priority}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 mb-2">{item.description}</p>
                      {item.response && (
                        <p className="text-xs text-gray-400 border-t border-[var(--border-color)] pt-2 mt-2">
                          <span className="text-green-400">响应：</span>{item.response}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 迭代总结 */}
          {reviewFeedback.iteration_summary && (
            <div className="px-6 py-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">迭代改进总结</h4>
              <div className="text-sm text-gray-300 space-y-2">
                {formatIterationSummary(reviewFeedback.iteration_summary)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReviewVisualizationCard;
