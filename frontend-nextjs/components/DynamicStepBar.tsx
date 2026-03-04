/**
 * 动态步骤条组件 - v8.2
 *
 * 根据后端推送的 active_steps 动态渲染步骤条
 * 支持批次节点展开查看专家执行详情
 * UI样式：横向进度条，圆形数字图标，连接线
 */

'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import {
  STEP_POOL,
  calculateStepStatus,
  extractAgentDisplayName,
  type BatchDetail,
  type StepStatus
} from '@/lib/workflow-steps-config';

interface DynamicStepBarProps {
  /** 后端推送的激活节点列表 */
  activeSteps: string[];
  /** 专家执行结果（用于判断完成状态） */
  agentResults: Record<string, any>;
  /** 批次执行详情（可选） */
  batchDetail?: BatchDetail;
}

export default function DynamicStepBar({
  activeSteps,
  agentResults,
  batchDetail
}: DynamicStepBarProps) {
  const [expandedBatch, setExpandedBatch] = useState(true);

  // 过滤掉跳过的步骤（不在 activeSteps 中）
  const visibleSteps = activeSteps
    .map(stepId => STEP_POOL[stepId])
    .filter(Boolean);

  return (
    <div className="dynamic-step-bar-container">
      {/* 横向进度条 */}
      <div className="step-progress-bar">
        {visibleSteps.map((step, index) => {
          const status = calculateStepStatus(step.id, activeSteps, agentResults, batchDetail);
          const isLast = index === visibleSteps.length - 1;

          return (
            <div key={step.id} className="step-wrapper">
              <div className="step-item-container">
                {/* 圆形图标 */}
                <div className={`step-circle ${status}`}>
                  {status === 'completed' ? (
                    <span className="checkmark">✓</span>
                  ) : (
                    <span className="step-number">{index + 1}</span>
                  )}
                </div>

                {/* 步骤名称 */}
                <div className={`step-label ${status}`}>
                  {step.label}
                </div>
              </div>

              {/* 连接线 */}
              {!isLast && (
                <div className={`step-connector ${status === 'completed' ? 'completed' : 'pending'}`} />
              )}
            </div>
          );
        })}
      </div>

      {/* 批次详情展开区域（如果有批次节点） */}
      {visibleSteps.some(step => step.batchNode) && batchDetail && (
        <div className="batch-detail-section mt-6">
          <div
            className="batch-header cursor-pointer flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
            onClick={() => setExpandedBatch(!expandedBatch)}
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">👥</span>
              <span className="font-medium">专家协作批次</span>
              <span className="batch-badge px-3 py-1 bg-blue-500 text-white rounded-full text-sm">
                第 {batchDetail.current_batch}/{batchDetail.total_batches} 批
              </span>
            </div>
            <ChevronDown
              className={`w-5 h-5 transition-transform ${expandedBatch ? 'rotate-180' : ''}`}
            />
          </div>

          {expandedBatch && (
            <div className="batch-detail mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              {/* 进度条 */}
              <div className="progress-bar-wrapper mb-4">
                <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                  <span>批次进度</span>
                  <span>{Math.round(batchDetail.batch_progress * 100)}%</span>
                </div>
                <div className="progress-bar h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="progress-fill h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${batchDetail.batch_progress * 100}%` }}
                  />
                </div>
              </div>

              {/* 专家网格 */}
              <div className="agents-grid grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {batchDetail.batch_agents.map(agentId => {
                  const isCompleted = batchDetail.completed_agents.includes(agentId);
                  const isActive = agentId === batchDetail.active_agent;
                  const agentStatus = isCompleted ? 'completed' : isActive ? 'active' : 'pending';

                  return (
                    <AgentBadge
                      key={agentId}
                      agentId={agentId}
                      status={agentStatus}
                    />
                  );
                })}
              </div>

              {/* 统计信息 */}
              <div className="mt-4 text-sm text-gray-600 dark:text-gray-400 text-center">
                已完成 {batchDetail.completed_agents.length}/{batchDetail.batch_agents.length} 位专家
              </div>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .dynamic-step-bar-container {
          width: 100%;
          padding: 20px 0;
        }

        /* 横向进度条 */
        .step-progress-bar {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          max-width: 1000px;
          margin: 0 auto;
          padding: 0 20px;
        }

        .step-wrapper {
          display: flex;
          align-items: center;
          flex: 1;
        }

        .step-item-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }

        /* 圆形图标 */
        .step-circle {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 18px;
          transition: all 0.3s ease;
          position: relative;
          z-index: 2;
        }

        .step-circle.pending {
          background: #e5e7eb;
          color: #9ca3af;
          border: 2px solid #d1d5db;
        }

        .step-circle.active {
          background: #3b82f6;
          color: white;
          border: 2px solid #3b82f6;
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
        }

        .step-circle.completed {
          background: #22c55e;
          color: white;
          border: 2px solid #22c55e;
        }

        .step-circle .checkmark {
          font-size: 24px;
        }

        /* 步骤名称 */
        .step-label {
          font-size: 14px;
          text-align: center;
          max-width: 120px;
          line-height: 1.4;
          transition: color 0.3s ease;
        }

        .step-label.pending {
          color: #9ca3af;
        }

        .step-label.active {
          color: #3b82f6;
          font-weight: 600;
        }

        .step-label.completed {
          color: #22c55e;
          font-weight: 500;
        }

        /* 连接线 */
        .step-connector {
          flex: 1;
          height: 2px;
          margin: 0 8px;
          position: relative;
          top: -30px;
          transition: background-color 0.3s ease;
        }

        .step-connector.pending {
          background: #d1d5db;
        }

        .step-connector.completed {
          background: #22c55e;
        }

        /* 响应式调整 */
        @media (max-width: 768px) {
          .step-circle {
            width: 40px;
            height: 40px;
            font-size: 16px;
          }

          .step-label {
            font-size: 12px;
            max-width: 80px;
          }

          .step-connector {
            margin: 0 4px;
          }
        }
      `}</style>
    </div>
  );
}

/**
 * 专家徽章子组件
 */
interface AgentBadgeProps {
  agentId: string;
  status: 'pending' | 'active' | 'completed';
}

function AgentBadge({ agentId, status }: AgentBadgeProps) {
  const displayName = extractAgentDisplayName(agentId);

  return (
    <div className={`agent-badge ${status} flex items-center gap-2 p-2 rounded-md transition-colors`}>
      <div className="agent-avatar w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm font-bold">
        {displayName[0]}
      </div>
      <div className="agent-name text-sm truncate flex-1">{displayName}</div>
      {status === 'completed' && (
        <span className="badge-icon text-green-500">✓</span>
      )}
      {status === 'active' && (
        <span className="badge-spinner">
          <div className="animate-pulse h-2 w-2 bg-blue-500 rounded-full" />
        </span>
      )}

      <style jsx>{`
        .agent-badge {
          transition: all 0.2s;
        }
        .agent-badge.pending {
          background: rgba(229, 231, 235, 0.5);
          color: #6b7280;
        }
        .agent-badge.active {
          background: rgba(59, 130, 246, 0.15);
          color: #3b82f6;
          border: 1px solid rgba(59, 130, 246, 0.3);
        }
        .agent-badge.completed {
          background: rgba(34, 197, 94, 0.15);
          color: #22c55e;
        }
      `}</style>
    </div>
  );
}
