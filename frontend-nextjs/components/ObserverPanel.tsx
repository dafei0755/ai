// components/ObserverPanel.tsx
// 方案图谱 — 旁路观察员面板（左侧）
// 只读·不写入·不推流程·观察项目概念关系可视化
// Copilot 生成 2026-03-15

'use client';

import { GitBranch, ExternalLink } from 'lucide-react';
import { SchemeGraph } from './SchemeGraph';

interface ObserverPanelProps {
  sessionId?: string;
  className?: string;
  onPopout?: () => void;
}

export function ObserverPanel({ sessionId, className = '', onPopout }: ObserverPanelProps) {
  return (
    <div
      className={`relative h-full bg-[var(--sidebar-bg)] overflow-hidden ${className}`}
    >
      {/* 图谱标题 + 外链按钮 — 叠加在图谱左上角 */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between z-10 pointer-events-none">
        <div className="flex items-center gap-1.5 text-[var(--foreground-secondary)]">
          <GitBranch className="w-3.5 h-3.5 text-[var(--primary)]" />
          <span className="text-xs font-medium">方案图谱</span>
        </div>
        {sessionId && (
          <button
            onClick={() => { window.open(`/scheme-graph?session=${sessionId}`, 'ObserverWindow', 'width=1200,height=800'); onPopout?.(); }}
            className="p-1 rounded text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] transition-colors pointer-events-auto"
            title="在独立窗口中打开观察屏"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Sigma.js 图谱（真实数据来自 graphStore） */}
      <SchemeGraph
        sessionId={sessionId}
        className="w-full h-full"
        showMockData={false}
      />
    </div>
  );
}

