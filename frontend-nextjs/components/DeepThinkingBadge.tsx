import React from 'react';
import { Brain } from 'lucide-react';

/**
 * 深度思考模式标识组件
 * 用于标识分析会话采用了深度思考模式（包含专家概念图生成）
 * 
 * @version v7.107
 */
export const DeepThinkingBadge: React.FC = () => {
  return (
    <div className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded text-xs font-medium">
      <Brain className="w-3 h-3" />
      <span>深度思考</span>
    </div>
  );
};

export default DeepThinkingBadge;
