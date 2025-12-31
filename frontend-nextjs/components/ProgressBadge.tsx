import React from 'react';

interface ProgressBadgeProps {
  progress?: number;
  currentStage?: string;
}

/**
 * 进度标识组件
 * 显示会话的执行进度和当前阶段
 *
 * @version v7.107
 */
export const ProgressBadge: React.FC<ProgressBadgeProps> = ({
  progress = 0,
  currentStage
}) => {
  const displayProgress = Math.round(progress * 100);

  return (
    <span className="text-xs text-gray-500">
      {displayProgress}%
      {currentStage && ` | ${currentStage}`}
    </span>
  );
};

export default ProgressBadge;
