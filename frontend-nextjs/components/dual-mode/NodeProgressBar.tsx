/**
 * NodeProgressBar.tsx — v2.0 双态需求分析 S1-S5 进度条
 * Created by GitHub Copilot · 2026-03-15
 *
 * 显示需求分析五步（S1~S5）的执行进度，供项目态页面嵌入使用。
 */

import React from 'react';

// ── 类型定义 ──────────────────────────────────────────────

export type StepStatus = 'pending' | 'running' | 'completed' | 'error';

export interface AnalysisStep {
  id: string;
  label: string;
  description: string;
  status: StepStatus;
}

interface NodeProgressBarProps {
  /** 当前正在执行的节点名称（来自 WebSocket status_update.current_node） */
  currentNode?: string;
  /** 整体 0-1 进度值 */
  progress?: number;
  /** 可选：外部直接传入步骤状态覆盖 */
  steps?: Partial<Record<string, StepStatus>>;
  className?: string;
}

// ── 默认步骤定义 ───────────────────────────────────────────

const DEFAULT_STEPS: AnalysisStep[] = [
  { id: 's1_input_decompose',     label: 'S1 输入解构',   description: '六维切片拆解用户输入',      status: 'pending' },
  { id: 's2_goal_locking',        label: 'S2 目标锁定',   description: '冲突检测 + 硬约束提取',    status: 'pending' },
  { id: 's3_strategy_framework',  label: 'S3 策略框架',   description: '四区 StrategyZone 构建', status: 'pending' },
  { id: 's4_tactics_decompose',   label: 'S4 战术分解',   description: 'DAG + ReviewGate 插入',  status: 'pending' },
  { id: 's5_compile_taskbook',    label: 'S5 任务书编译', description: '冻结需求 → DesignTaskBook', status: 'pending' },
];

/** 根据 currentNode 推断步骤状态 */
function deriveStepStatuses(
  currentNode: string | undefined,
  overrides: Partial<Record<string, StepStatus>> = {}
): AnalysisStep[] {
  const order = DEFAULT_STEPS.map((s) => s.id);
  const currentIdx = currentNode ? order.indexOf(currentNode) : -1;

  return DEFAULT_STEPS.map((step, idx) => {
    if (overrides[step.id]) return { ...step, status: overrides[step.id]! };
    if (idx < currentIdx) return { ...step, status: 'completed' };
    if (idx === currentIdx) return { ...step, status: 'running' };
    return { ...step, status: 'pending' };
  });
}

// ── 状态颜色映射 ────────────────────────────────────────────

const STATUS_STYLES: Record<StepStatus, { dot: string; label: string; bar: string }> = {
  pending:   { dot: 'bg-gray-300',    label: 'text-gray-400',  bar: 'bg-gray-200' },
  running:   { dot: 'bg-blue-500 animate-pulse', label: 'text-blue-600 font-semibold', bar: 'bg-blue-400' },
  completed: { dot: 'bg-green-500',   label: 'text-green-700', bar: 'bg-green-400' },
  error:     { dot: 'bg-red-500',     label: 'text-red-600',   bar: 'bg-red-400'   },
};

// ── 组件 ────────────────────────────────────────────────────

const NodeProgressBar: React.FC<NodeProgressBarProps> = ({
  currentNode,
  progress = 0,
  steps: overrides = {},
  className = '',
}) => {
  const steps = deriveStepStatuses(currentNode, overrides);
  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const pct = Math.round(progress * 100);

  return (
    <div className={`w-full ${className}`}>
      {/* 顶部总进度 */}
      <div className="flex items-center justify-between mb-2 text-xs text-gray-500">
        <span className="font-medium text-gray-700">需求分析进度</span>
        <span>{completedCount} / {steps.length} 步完成 · {pct}%</span>
      </div>

      {/* 总进度条 */}
      <div className="w-full h-1.5 bg-gray-200 rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* 步骤列表 */}
      <ol className="space-y-2">
        {steps.map((step) => {
          const style = STATUS_STYLES[step.status];
          return (
            <li key={step.id} className="flex items-start gap-3">
              {/* 状态点 */}
              <span className={`mt-1 flex-shrink-0 w-2.5 h-2.5 rounded-full ${style.dot}`} />

              <div className="flex-1 min-w-0">
                <div className={`text-sm ${style.label}`}>
                  {step.label}
                </div>
                <div className="text-xs text-gray-400 truncate">{step.description}</div>
              </div>

              {/* 运行中：短动画横条 */}
              {step.status === 'running' && (
                <div className="flex-shrink-0 w-16 h-1.5 mt-1.5 bg-blue-100 rounded overflow-hidden">
                  <div className="h-full w-8 bg-blue-400 rounded animate-bounce" />
                </div>
              )}

              {/* 完成：对勾 */}
              {step.status === 'completed' && (
                <span className="flex-shrink-0 text-green-500 text-xs mt-0.5">✓</span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
};

export default NodeProgressBar;
