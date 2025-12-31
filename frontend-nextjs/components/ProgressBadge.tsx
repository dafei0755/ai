import React from 'react';
import { Loader2 } from 'lucide-react';

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
    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded text-xs font-medium">
      <Loader2 className="w-3 h-3 animate-spin" />
      <span>{displayProgress}%</span>
      {currentStage && (
        <span className="text-gray-400">| {currentStage}</span>
      )}
    </div>
  );
};

export default ProgressBadge;
