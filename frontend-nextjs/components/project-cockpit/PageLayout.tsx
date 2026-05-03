'use client';

import type { ReactNode } from 'react';

interface PageLayoutProps {
  leftNav: ReactNode;     // 浮动胶囊导航（内部绝对定位）
  mainContent: ReactNode; // 含 header + body 的完整面板
  advisorPanel: ReactNode;
}

export function PageLayout({ leftNav, mainContent, advisorPanel }: PageLayoutProps) {
  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden">
      {/* 左侧内容区 */}
      <div className="flex-1 overflow-hidden relative flex flex-col min-w-0">
        {/* 浮动胶囊导航 — 绝对定位叠在内容上方 */}
        <div className="absolute top-4 left-3 z-20 flex flex-col items-start gap-3">
          {leftNav}
        </div>
        {/* 主内容面板（含 sticky header + scroll body） */}
        <div className="flex flex-col h-full min-h-0 cockpit-panel-root">
          {mainContent}
        </div>
      </div>

      {/* 右侧方案高参 */}
      <div className="w-[30rem] shrink-0 border-l border-black/10 bg-[#161616] text-white flex flex-col overflow-hidden">
        {advisorPanel}
      </div>
    </div>
  );
}
