/**
 * DeltaOrDeriveSelector.tsx — v2.0 局部修订 vs 重大派生选择器
 * Created by GitHub Copilot · 2026-03-15
 *
 * 当用户提交增量修改请求时，展示 DeltaRouter 的判断结果
 * 并让用户选择确认"局部修订（Delta）"还是"重大派生（Derived）"。
 *
 * 流程：
 *   1. 后端 /api/v2/project/{session_id}/delta 返回 delta_type + impact_graph
 *   2. 本组件展示影响范围
 *   3. 用户确认 → 触发 onConfirm 回调
 *   4. 用户取消 → 关闭弹窗
 */

import React, { useState } from 'react';

// ── 类型定义 ──────────────────────────────────────────────

export type DeltaType = 'delta' | 'derived';

export interface ImpactGraphSummary {
  /** 受影响的节点 ID 列表 */
  affected_nodes?: string[];
  /** 是否需要派生新项目 */
  requires_derived_project?: boolean;
  /** 影响层级描述 */
  impact_scope?: string;
  /** 受影响的约束 */
  affected_constraints?: string[];
}

interface DeltaOrDeriveSelectorProps {
  /** 后端返回的路由类型 */
  deltaType: DeltaType;
  /** 用户原始修改意图 */
  modificationText: string;
  /** 影响图摘要 */
  impactGraph?: ImpactGraphSummary | null;
  /** 加载中 */
  loading?: boolean;
  /** 确认回调：传入用户最终选择的类型 */
  onConfirm: (type: DeltaType) => void;
  /** 取消回调 */
  onCancel: () => void;
  className?: string;
}

// ── 辅助组件 ────────────────────────────────────────────────

function TypeCard({
  type,
  selected,
  onClick,
}: {
  type: DeltaType;
  selected: boolean;
  onClick: () => void;
}) {
  const isDelta = type === 'delta';
  const border = selected
    ? isDelta ? 'border-blue-500 bg-blue-50' : 'border-orange-500 bg-orange-50'
    : 'border-gray-200 bg-white hover:border-gray-300';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border-2 transition-all ${border}`}
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{isDelta ? '✏️' : '🌿'}</span>
        <div>
          <div className={`text-sm font-semibold ${selected ? (isDelta ? 'text-blue-700' : 'text-orange-700') : 'text-gray-800'}`}>
            {isDelta ? '局部修订（Delta）' : '重大派生（Derived）'}
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            {isDelta
              ? '直接更新现有项目的相关节点，保留大部分设计决策'
              : '创建新的项目版本，保留原版本作为历史快照'}
          </div>
        </div>
        {selected && (
          <span className={`ml-auto text-lg flex-shrink-0 ${isDelta ? 'text-blue-500' : 'text-orange-500'}`}>✓</span>
        )}
      </div>

      {/* 特点列表 */}
      <ul className="pl-8 space-y-0.5 text-xs text-gray-500">
        {isDelta ? (
          <>
            <li>• 修改范围局限于特定节点</li>
            <li>• 执行速度快，成本低</li>
            <li>• 不影响整体设计框架</li>
          </>
        ) : (
          <>
            <li>• 修改幅度大，影响核心框架</li>
            <li>• 原项目完整保留可对比</li>
            <li>• 适合方向性调整或重大需求变更</li>
          </>
        )}
      </ul>
    </button>
  );
}

// ── 主组件 ──────────────────────────────────────────────────

const DeltaOrDeriveSelector: React.FC<DeltaOrDeriveSelectorProps> = ({
  deltaType,
  modificationText,
  impactGraph,
  loading = false,
  onConfirm,
  onCancel,
  className = '',
}) => {
  const [selected, setSelected] = useState<DeltaType>(deltaType);

  const affectedCount = impactGraph?.affected_nodes?.length ?? 0;

  return (
    <div className={`rounded-xl border bg-white shadow-lg p-6 space-y-5 max-w-lg mx-auto ${className}`}>
      {/* 标题 */}
      <div>
        <h3 className="text-base font-semibold text-gray-800">选择修改方式</h3>
        <p className="text-xs text-gray-500 mt-1">
          系统已分析你的修改意图，推荐使用{' '}
          <span className={`font-medium ${deltaType === 'delta' ? 'text-blue-600' : 'text-orange-600'}`}>
            {deltaType === 'delta' ? '局部修订' : '重大派生'}
          </span>
          ，你也可以手动选择。
        </p>
      </div>

      {/* 修改意图摘要 */}
      <div className="p-3 rounded-lg bg-gray-50 border text-sm text-gray-700">
        <div className="text-xs text-gray-400 mb-1">修改意图</div>
        <div className="line-clamp-3">{modificationText}</div>
      </div>

      {/* 影响范围 */}
      {impactGraph && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase">影响范围分析</div>
          <div className="grid grid-cols-2 gap-2">
            {affectedCount > 0 && (
              <div className="p-2 rounded-lg bg-amber-50 border border-amber-100 text-xs">
                <span className="font-medium text-amber-700">{affectedCount} 个节点</span>
                <div className="text-amber-500">受到影响</div>
              </div>
            )}
            {impactGraph.impact_scope && (
              <div className="p-2 rounded-lg bg-blue-50 border border-blue-100 text-xs">
                <span className="font-medium text-blue-700">影响层级</span>
                <div className="text-blue-500 truncate">{impactGraph.impact_scope}</div>
              </div>
            )}
          </div>
          {impactGraph.affected_constraints && impactGraph.affected_constraints.length > 0 && (
            <div className="text-xs text-red-600 flex items-start gap-1">
              <span>⚠</span>
              <span>将影响硬约束：{impactGraph.affected_constraints.join('、')}</span>
            </div>
          )}
        </div>
      )}

      {/* 选择卡片 */}
      <div className="space-y-3">
        <TypeCard type="delta"   selected={selected === 'delta'}   onClick={() => setSelected('delta')} />
        <TypeCard type="derived" selected={selected === 'derived'} onClick={() => setSelected('derived')} />
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3 pt-2">
        <button
          onClick={onCancel}
          disabled={loading}
          className="flex-1 py-2.5 text-sm font-medium rounded-lg border text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          取消
        </button>
        <button
          onClick={() => onConfirm(selected)}
          disabled={loading}
          className={`flex-1 py-2.5 text-sm font-medium rounded-lg text-white transition-colors disabled:opacity-50 ${
            selected === 'delta'
              ? 'bg-blue-600 hover:bg-blue-700'
              : 'bg-orange-500 hover:bg-orange-600'
          }`}
        >
          {loading ? '处理中…' : `确认${selected === 'delta' ? '局部修订' : '重大派生'}`}
        </button>
      </div>
    </div>
  );
};

export default DeltaOrDeriveSelector;
