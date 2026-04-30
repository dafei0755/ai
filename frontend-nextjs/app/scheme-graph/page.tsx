// app/scheme-graph/page.tsx
// 方案图谱 — 独立观察屏（全屏窗口）
// 通过 BroadcastChannel 与主窗口同步图谱状态
// Copilot 生成 2026-03-15

'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { GitBranch, X } from 'lucide-react';
import { SchemeGraph } from '@/components/SchemeGraph';
import { useGraphStore, GraphHint } from '@/store/graphStore';
import type { GraphNode, GraphEdge } from '@/store/graphStore';

export default function SchemeGraphPage() {
  const searchParams = useSearchParams();
  const sessionId    = searchParams.get('session') ?? undefined;
  const channelRef   = useRef<BroadcastChannel | null>(null);
  const { applyGraphHint, promoteAllPendingToStable, setStableState } = useGraphStore();

  // BroadcastChannel：接收主窗口推送的图谱事件
  useEffect(() => {
    const channel = new BroadcastChannel('scheme-graph-sync');
    channelRef.current = channel;

    channel.onmessage = (e: MessageEvent) => {
      const { type, payload } = e.data ?? {};
      switch (type) {
        case 'GRAPH_HINT':
          // Phase 2：主窗口推送 graph_hint，观察屏直接应用
          if (payload?.hint) applyGraphHint(payload.hint as GraphHint);
          break;
        case 'PROMOTE_ALL':
          // 用户在主窗口确认中断点 → 所有 pending 提升为 stable
          promoteAllPendingToStable();
          break;
        case 'FULL_SYNC':
          // 主窗口推送完整 stable 图谱快照 → 直接替换本窗口 store
          if (payload?.nodes && payload?.edges) {
            setStableState(payload.nodes as GraphNode[], payload.edges as GraphEdge[]);
          }
          break;
        default:
          break;
      }
    };

    // 通知主窗口：观察屏已就绪
    channel.postMessage({ type: 'OBSERVER_READY', sessionId });

    // 窗口关闭时通知主窗口恢复左侧面板
    const handleUnload = () => channel.postMessage({ type: 'OBSERVER_CLOSED', sessionId });
    window.addEventListener('beforeunload', handleUnload);

    return () => {
      window.removeEventListener('beforeunload', handleUnload);
      channel.close();
    };
  }, [sessionId, applyGraphHint, promoteAllPendingToStable, setStableState]);

  return (
    <div className="w-screen h-screen bg-[var(--background)] flex flex-col overflow-hidden">
      {/* 顶部栏 */}
      <header className="shrink-0 h-10 px-4 flex items-center justify-between border-b border-[var(--border)] bg-[var(--sidebar-bg)]">
        <div className="flex items-center gap-2 text-[var(--foreground-secondary)]">
          <GitBranch className="w-4 h-4 text-[var(--primary)]" />
          <span className="text-sm font-medium">方案图谱观察屏</span>
          {sessionId && (
            <span className="text-xs opacity-50 ml-1">· {sessionId.slice(0, 8)}…</span>
          )}
        </div>
        <button
          onClick={() => window.close()}
          className="p-1.5 rounded text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] transition-colors"
          title="关闭观察屏"
        >
          <X className="w-4 h-4" />
        </button>
      </header>

      {/* 图谱全屏区域 */}
      <main className="flex-1 overflow-hidden">
        <SchemeGraph
          sessionId={sessionId}
          className="w-full h-full"
          showMockData={false}
        />
      </main>

      {/* 底部状态栏 */}
      <footer className="shrink-0 h-7 px-4 flex items-center gap-2 border-t border-[var(--border)] bg-[var(--sidebar-bg)]">
        <span className="text-[10px] text-[var(--foreground-secondary)] opacity-50">
          只读观察面板 · 任何操作均不影响主生产链
        </span>
      </footer>
    </div>
  );
}
