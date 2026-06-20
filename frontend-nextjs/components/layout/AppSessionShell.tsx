'use client';

import type { ReactNode, RefObject } from 'react';
import { PanelLeft } from 'lucide-react';
import { SessionSidebar, type Session } from '@/components/SessionSidebar';
import { UserPanel } from '@/components/layout/UserPanel';

interface AppSessionShellProps {
  children: ReactNode;
  isSidebarOpen: boolean;
  onSidebarOpenChange: (open: boolean) => void;
  sessions: Session[];
  currentSessionId?: string;
  sidebarNavigationMode?: 'new-tab' | 'in-place';
  onRenameSession?: (sessionId: string) => void;
  onPinSession?: (sessionId: string) => void;
  onShareSession?: (sessionId: string) => void;
  onDeleteSession?: (sessionId: string) => void;
  loadMoreTriggerRef?: RefObject<HTMLDivElement | null>;
  showExternalLink?: boolean;
}

export function AppSessionShell({
  children,
  isSidebarOpen,
  onSidebarOpenChange,
  sessions,
  currentSessionId,
  sidebarNavigationMode = 'new-tab',
  onRenameSession,
  onPinSession,
  onShareSession,
  onDeleteSession,
  loadMoreTriggerRef,
  showExternalLink = false,
}: AppSessionShellProps) {
  const isInIframe = typeof window !== 'undefined' && window.self !== window.top;

  return (
    <div className="ucppt-advisor-shell flex h-screen flex-col overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      <div className="relative flex flex-1 overflow-hidden">
        {isSidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/50 md:hidden"
            onClick={() => onSidebarOpenChange(false)}
          />
        )}

        <div
          className={`${
            isSidebarOpen ? 'w-[310px] translate-x-0' : 'w-0 -translate-x-full md:w-0 md:translate-x-0'
          } fixed z-40 flex h-full flex-col overflow-hidden bg-[var(--sidebar-bg)] transition-all duration-300 ease-in-out md:relative`}
        >
          {isSidebarOpen && (
            <>
              <div className="h-0 min-w-[310px] pt-4" />
              <div className="flex min-h-0 flex-1 flex-col">
                <SessionSidebar
                  sessions={sessions}
                  currentSessionId={currentSessionId}
                  navigationMode={sidebarNavigationMode}
                  onRenameSession={onRenameSession}
                  onPinSession={onPinSession}
                  onShareSession={onShareSession}
                  onDeleteSession={onDeleteSession}
                  loadMoreTriggerRef={loadMoreTriggerRef}
                />
              </div>

              <div className="min-w-[310px] flex-shrink-0 border-t border-[var(--border-color)]">
                <div className="p-3">
                  <UserPanel />
                </div>
              </div>
            </>
          )}
        </div>

        <div className="flex w-full flex-1 flex-col">
          {/* 顶部标题栏：占据实际高度，内容区从此行下方开始，避免重叠 */}
          <div className="flex flex-shrink-0 items-center gap-2 px-4 py-2">
            <button
              type="button"
              onClick={() => onSidebarOpenChange(!isSidebarOpen)}
              className="rounded-lg p-2 text-[var(--foreground-secondary)] transition-colors hover:bg-[var(--card-bg)] hover:text-[var(--foreground)]"
              title={isSidebarOpen ? '关闭侧边栏' : '打开侧边栏'}
              aria-label={isSidebarOpen ? '关闭侧边栏' : '打开侧边栏'}
            >
              <PanelLeft size={20} />
            </button>

            {showExternalLink && !isInIframe && (
              <a
                href="https://www.ucppt.com/js"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-[var(--foreground-secondary)] transition-colors hover:bg-[var(--card-bg)] hover:text-[var(--foreground)]"
                title="返回 ucppt.com/js"
              >
                <span>设计知外 ucppt.com</span>
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            )}
          </div>

          <div className="min-h-0 flex-1 flex flex-col">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
