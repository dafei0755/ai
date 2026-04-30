/**
 * 维度反馈模态框组件
 *
 * 在用户完成Step 2（雷达图填写）后延迟弹出，
 * 收集对维度有用性的评分反馈（1-5星），用于学习系统优化。
 */

import React, { useState } from 'react';
import { Star, X } from 'lucide-react';
import { toast } from 'sonner';

interface Dimension {
  id: string;
  name: string;
  left_label?: string;
  right_label?: string;
}

interface DimensionFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  dimensions: Dimension[];
  sessionId: string;
}

/**
 * 星级评分组件
 */
function StarRating({
  value,
  onChange,
  dimensionName
}: {
  value: number;
  onChange: (rating: number) => void;
  dimensionName: string;
}) {
  const [hoverRating, setHoverRating] = useState(0);

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHoverRating(star)}
          onMouseLeave={() => setHoverRating(0)}
          className="transition-transform hover:scale-110 focus:outline-none"
          aria-label={`给 ${dimensionName} 评 ${star} 星`}
        >
          <Star
            className={`w-6 h-6 ${
              star <= (hoverRating || value)
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-gray-300'
            } transition-colors`}
          />
        </button>
      ))}
    </div>
  );
}

export function DimensionFeedbackModal({
  isOpen,
  onClose,
  dimensions,
  sessionId,
}: DimensionFeedbackModalProps) {
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [feedbackText, setFeedbackText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [startTime] = useState(Date.now());

  const handleSubmit = async () => {
    // 至少需要评价一个维度
    if (Object.keys(ratings).length === 0) {
      toast.error('请至少为一个维度评分');
      return;
    }

    setIsSubmitting(true);

    try {
      const completionTime = (Date.now() - startTime) / 1000; // 转换为秒

      const response = await fetch('/api/v1/dimensions/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          dimension_ratings: ratings,
          feedback_text: feedbackText || undefined,
          completion_time: completionTime,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '提交失败');
      }

      const result = await response.json();

      toast.success(`${result.message}（平均评分: ${result.avg_rating?.toFixed(1)} 分）`);
      onClose();
    } catch (error) {
      console.error('[DimensionFeedback] 提交失败:', error);
      toast.error(error instanceof Error ? error.message : '提交失败，请稍后重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  const getRatingLabel = (rating: number): string => {
    const labels = {
      1: '无用',
      2: '用处不大',
      3: '一般',
      4: '有用',
      5: '非常有用',
    };
    return labels[rating as keyof typeof labels] || '';
  };

  const ratedCount = Object.keys(ratings).length;
  const avgRating = ratedCount > 0
    ? Object.values(ratings).reduce((a, b) => a + b, 0) / ratedCount
    : 0;

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col mx-4">
            {/* Header */}
            <div className="p-6 border-b">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Star className="w-5 h-5 text-yellow-500" />
                    维度有用性反馈（可选）
                  </h2>
                  <p className="text-sm text-gray-600 mt-2">
                    哪些维度对您的需求最有帮助？您的反馈将帮助我们改进推荐算法。
                    <span className="text-xs text-gray-500 ml-2">
                      （已评价 {ratedCount}/{dimensions.length}，平均 {avgRating.toFixed(1)} 分）
                    </span>
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                  aria-label="关闭"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Body - Scrollable */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                {dimensions.map((dim) => (
                  <div
                    key={dim.id}
                    className="flex items-start justify-between gap-4 p-3 rounded-lg border hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-sm truncate">{dim.name}</h4>
                      {dim.left_label && dim.right_label && (
                        <p className="text-xs text-gray-500 mt-1">
                          {dim.left_label} ← → {dim.right_label}
                        </p>
                      )}
                      {ratings[dim.id] && (
                        <p className="text-xs text-blue-600 mt-1 font-medium">
                          {getRatingLabel(ratings[dim.id])}
                        </p>
                      )}
                    </div>
                    <StarRating
                      value={ratings[dim.id] || 0}
                      onChange={(rating) => {
                        setRatings((prev) => ({ ...prev, [dim.id]: rating }));
                      }}
                      dimensionName={dim.name}
                    />
                  </div>
                ))}

                <div className="pt-4">
                  <label
                    htmlFor="feedback-text"
                    className="block text-sm font-medium mb-2"
                  >
                    其他建议（可选）
                  </label>
                  <textarea
                    id="feedback-text"
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    placeholder="例如：哪些维度特别有用？哪些维度不太适用您的项目？"
                    className="w-full h-24 px-3 py-2 text-sm border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    maxLength={500}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {feedbackText.length}/500
                  </p>
                </div>
              </div>

              <div className="border-t pt-4 mt-6">
                <h5 className="text-sm font-medium mb-2">评分标准</h5>
                <ul className="text-xs text-gray-600 space-y-1">
                  <li>⭐ 1星：完全不相关，对项目无帮助</li>
                  <li>⭐⭐ 2星：关联不强，参考价值有限</li>
                  <li>⭐⭐⭐ 3星：有一定参考价值</li>
                  <li>⭐⭐⭐⭐ 4星：很有用，提供了有价值的思考角度</li>
                  <li>⭐⭐⭐⭐⭐ 5星：非常有用，帮助明确了关键需求</li>
                </ul>
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t flex justify-end gap-3">
              <button
                onClick={handleSkip}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                跳过
              </button>
              <button
                onClick={handleSubmit}
                disabled={isSubmitting || ratedCount === 0}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? '提交中...' : `提交反馈 (${ratedCount}/${dimensions.length})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
