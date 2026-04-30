/**
 * UCPPT搜索进度指示器 - v7.270
 *
 * 展示两步流程的进度：
 * Step 1: 需求理解与深度分析 → Step 2: 搜索框架生成 → 搜索执行
 */

import React from 'react';

export type UcpptSearchPhase = 'step1' | 'step2' | 'searching' | 'completed';

interface UcpptSearchProgressProps {
  currentPhase: UcpptSearchPhase;
  step1Status?: 'pending' | 'in_progress' | 'completed';
  step2Status?: 'pending' | 'in_progress' | 'completed';
  searchStatus?: 'pending' | 'in_progress' | 'completed';
  className?: string;
}

export const UcpptSearchProgress: React.FC<UcpptSearchProgressProps> = ({
  currentPhase,
  step1Status = 'pending',
  step2Status = 'pending',
  searchStatus = 'pending',
  className = '',
}) => {
  const steps = [
    {
      id: 'step1',
      label: 'Step 1',
      description: '需求理解与深度分析',
      icon: '🧠',
      status: step1Status,
    },
    {
      id: 'step2',
      label: 'Step 2',
      description: '搜索框架生成',
      icon: '📋',
      status: step2Status,
    },
    {
      id: 'searching',
      label: '搜索执行',
      description: '目标导向搜索',
      icon: '🔍',
      status: searchStatus,
    },
  ];

  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500 border-green-500 text-white';
      case 'in_progress':
        return 'bg-blue-500 border-blue-500 text-white animate-pulse';
      case 'pending':
      default:
        return 'bg-gray-200 border-gray-300 text-gray-500';
    }
  };

  const getConnectorColor = (prevStatus: string) => {
    return prevStatus === 'completed' ? 'bg-green-500' : 'bg-gray-300';
  };

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <React.Fragment key={step.id}>
            {/* 步骤节点 */}
            <div className="flex flex-col items-center flex-1">
              {/* 圆形图标 */}
              <div
                className={`w-16 h-16 rounded-full border-2 flex items-center justify-center text-2xl transition-all duration-300 ${getStepColor(
                  step.status
                )}`}
              >
                {step.status === 'in_progress' ? (
                  <div className="animate-spin">⚙️</div>
                ) : (
                  step.icon
                )}
              </div>

              {/* 标签 */}
              <div className="mt-3 text-center">
                <div className="text-sm font-semibold text-gray-900">{step.label}</div>
                <div className="text-xs text-gray-600 mt-1">{step.description}</div>
              </div>

              {/* 状态指示 */}
              <div className="mt-2">
                {step.status === 'completed' && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    ✓ 已完成
                  </span>
                )}
                {step.status === 'in_progress' && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    ⚡ 进行中
                  </span>
                )}
                {step.status === 'pending' && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    ⏳ 等待中
                  </span>
                )}
              </div>
            </div>

            {/* 连接线 */}
            {index < steps.length - 1 && (
              <div className="flex-1 px-4">
                <div className={`h-1 rounded-full transition-all duration-500 ${getConnectorColor(step.status)}`} />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default UcpptSearchProgress;
