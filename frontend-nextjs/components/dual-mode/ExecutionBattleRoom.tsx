/**
 * ExecutionBattleRoom.tsx — v2.0 执行态实时状态看板
 * Created by GitHub Copilot · 2026-03-15
 *
 * 展示项目执行阶段（ExecutionOrchestrator）的实时进度：
 *   - DAG 批次进度
 *   - 当前执行的 deliverable 节点
 *   - ReviewGate 评审状态
 *   - 预算消耗指示
 */

import React from 'react';

// ── 类型定义 ──────────────────────────────────────────────

export type ExecNodeStatus = 'pending' | 'running' | 'review' | 'completed' | 'halted';

export interface ExecDeliverable {
  node_id: string;
  name: string;
  role: string;
  status: ExecNodeStatus;
  /** 0-1 完成度 */
  progress?: number;
  review_gate?: {
    passed: boolean;
    quality_score?: number;
    redline_violations?: string[];
  } | null;
}

export interface ReviewGateInfo {
  gate_id: string;
  status: 'pending' | 'evaluating' | 'passed' | 'failed' | 'waiting_human';
  triggered_at?: string;
}

interface ExecutionBattleRoomProps {
  /** 总体进度 0-1 */
  overallProgress?: number;
  /** 当前批次 / 总批次 */
  currentBatch?: number;
  totalBatches?: number;
  /** 可交付物节点列表 */
  deliverables?: ExecDeliverable[];
  /** 当前 review gate 状态 */
  activeReviewGate?: ReviewGateInfo | null;
  /** 预算已用 token 数 */
  budgetUsed?: number;
  /** 预算上限 token 数 */
  budgetLimit?: number;
  /** 是否已暂停 */
  halted?: boolean;
  haltReason?: string;
  className?: string;
}

// ── 辅助 ────────────────────────────────────────────────────

const NODE_STATUS_STYLE: Record<ExecNodeStatus, string> = {
  pending:   'bg-gray-100 text-gray-500 border-gray-200',
  running:   'bg-blue-50  text-blue-700  border-blue-300',
  review:    'bg-yellow-50 text-yellow-700 border-yellow-300',
  completed: 'bg-green-50 text-green-700 border-green-200',
  halted:    'bg-red-50   text-red-700   border-red-200',
};

const NODE_ICON: Record<ExecNodeStatus, string> = {
  pending:   '○',
  running:   '▶',
  review:    '🔍',
  completed: '✓',
  halted:    '⏸',
};

function BudgetBar({ used, limit }: { used: number; limit: number }) {
  if (!limit) return null;
  const pct = Math.min(100, Math.round((used / limit) * 100));
  const color = pct > 80 ? 'bg-red-500' : pct > 60 ? 'bg-yellow-400' : 'bg-green-400';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>Token 预算</span>
        <span>{used.toLocaleString()} / {limit.toLocaleString()} ({pct}%)</span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── 组件 ────────────────────────────────────────────────────

const ExecutionBattleRoom: React.FC<ExecutionBattleRoomProps> = ({
  overallProgress = 0,
  currentBatch = 0,
  totalBatches = 0,
  deliverables = [],
  activeReviewGate,
  budgetUsed = 0,
  budgetLimit = 0,
  halted = false,
  haltReason,
  className = '',
}) => {
  const pct = Math.round(overallProgress * 100);
  const completedCount = deliverables.filter((d) => d.status === 'completed').length;

  return (
    <div className={`rounded-xl border bg-white shadow-sm p-5 space-y-5 ${className}`}>
      {/* 标题行 */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-800">执行态 · 实时看板</h3>
        {halted && (
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700 border border-red-200">
            已暂停
          </span>
        )}
        {!halted && overallProgress >= 1 && (
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700 border border-green-200">
            执行完成
          </span>
        )}
      </div>

      {/* 总进度 */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-gray-500">
          <span>总进度</span>
          <span>
            {totalBatches > 0 ? `批次 ${currentBatch}/${totalBatches} · ` : ''}
            {completedCount}/{deliverables.length} 交付物 · {pct}%
          </span>
        </div>
        <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden border">
          <div
            className={`h-full rounded-full transition-all duration-700 ${halted ? 'bg-red-400' : 'bg-blue-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* 暂停原因 */}
      {halted && haltReason && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-100 text-xs text-red-700">
          ⏸ 暂停原因：{haltReason}
        </div>
      )}

      {/* ReviewGate 状态 */}
      {activeReviewGate && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
          <span className="text-yellow-500 text-lg">🔍</span>
          <div className="flex-1">
            <div className="text-sm font-medium text-yellow-800">ReviewGate 评审中</div>
            <div className="text-xs text-yellow-600">
              {activeReviewGate.gate_id} · 状态：{activeReviewGate.status}
            </div>
          </div>
        </div>
      )}

      {/* 交付物节点列表 */}
      {deliverables.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">交付物节点</div>
          <div className="grid gap-2 sm:grid-cols-2">
            {deliverables.map((d) => (
              <div
                key={d.node_id}
                className={`flex items-start gap-2 p-2.5 rounded-lg border text-xs ${NODE_STATUS_STYLE[d.status]}`}
              >
                <span className="flex-shrink-0 font-mono">{NODE_ICON[d.status]}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{d.name}</div>
                  <div className="text-gray-400 truncate">{d.role}</div>
                  {d.status === 'running' && typeof d.progress === 'number' && (
                    <div className="mt-1 w-full h-1 bg-white/60 rounded overflow-hidden">
                      <div
                        className="h-full bg-blue-400 rounded transition-all duration-500"
                        style={{ width: `${Math.round(d.progress * 100)}%` }}
                      />
                    </div>
                  )}
                  {d.review_gate && !d.review_gate.passed && d.review_gate.redline_violations?.length && (
                    <div className="mt-1 text-red-500 truncate">
                      ⚠ {d.review_gate.redline_violations[0]}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Token 预算 */}
      {budgetLimit > 0 && <BudgetBar used={budgetUsed} limit={budgetLimit} />}
    </div>
  );
};

export default ExecutionBattleRoom;
