'use client';

import type { ReactNode } from 'react';

interface PageLayoutProps {
  leftNav: ReactNode;
  mainContent: ReactNode;
  middlePanel?: ReactNode;
  advisorPanel: ReactNode;
}

export function PageLayout({ leftNav, mainContent, middlePanel, advisorPanel }: PageLayoutProps) {
  return (
    <div
      className={`project-workspace-three-column-shell h-screen bg-[var(--background)] text-[var(--foreground)] ${
        middlePanel ? 'project-workspace-three-column-shell-with-middle' : 'project-workspace-three-column-shell-two-column'
      }`}
    >
      <div className="project-workspace-main-column project-workspace-canvas-column relative flex min-w-0 flex-col overflow-hidden">
        <div className="absolute top-4 left-3 z-20 flex flex-col items-start gap-3">
          {leftNav}
        </div>
        <div className="flex flex-col h-full min-h-0 cockpit-panel-root">
          {mainContent}
        </div>
      </div>

      {middlePanel && (
        <div className="project-workspace-middle-column cursor-default border-l border-black/10 bg-white text-slate-900">
          {middlePanel}
        </div>
      )}

      <div className="project-workspace-advisor-column border-l border-black/10 bg-[#161616] text-white">
        {advisorPanel}
      </div>
    </div>
  );
}
