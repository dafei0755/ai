'use client';

import type { ReactNode, RefObject } from 'react';
import { PanelLeft } from 'lucide-react';

import { SessionSidebar, type Session } from '@/components/SessionSidebar';
import { UserPanel } from '@/components/layout/UserPanel';

export type AppSessionShellNavigationMode = 'new-tab' | 'in-place';

export type AppSessionShellSession = Omit<Session, 'user_input'> & {
  user_input?: string;
};

type AppSessionShellProps = {
  children: ReactNode;
  isSidebarOpen: boolean;
  onSidebarOpenChange: (open: boolean) => void;
  sessions: AppSessionShellSession[];
  currentSessionId?: string;
  sidebarNavigationMode?: AppSessionShellNavigationMode;
  showExternalLink?: boolean;
  onRenameSession?: (sessionId: string) => void;
  onPinSession?: (sessionId: string) => void;
  onShareSession?: (sessionId: string) => void;
  onDeleteSession?: (sessionId: string) => void;
  loadMoreTriggerRef?: RefObject<HTMLDivElement | null>;
};

const normalizeSessions = (sessions: AppSessionShellSession[]): Session[] =>
  sessions.map((session) => ({
    ...session,
    user_input: session.user_input ?? session.display_name ?? '',
  }));

export function AppSessionShell({
  children,
  isSidebarOpen,
  onSidebarOpenChange,
  sessions,
  currentSessionId,
  sidebarNavigationMode = 'new-tab',
  showExternalLink = false,
  onRenameSession,
  onPinSession,
  onShareSession,
  onDeleteSession,
  loadMoreTriggerRef,
}: AppSessionShellProps) {
  const normalizedSessions = normalizeSessions(sessions);

  return (
    <div className="ucppt-advisor-shell flex h-screen flex-col overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        {isSidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/50 md:hidden"
            onClick={() => onSidebarOpenChange(false)}
          />
        )}

        <aside
          className={`${
            isSidebarOpen ? 'w-[310px] translate-x-0' : 'w-0 -translate-x-full md:w-0 md:translate-x-0'
          } fixed z-40 flex h-full flex-col overflow-hidden border-r border-[var(--border-color)] bg-[var(--sidebar-bg)] transition-all duration-300 ease-in-out md:relative`}
        >
          {isSidebarOpen && (
            <>
              <div className="h-0 min-w-[310px] pt-4" />
              <div className="flex min-h-0 flex-1 flex-col">
                <SessionSidebar
                  sessions={normalizedSessions}
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
        </aside>

        <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
          <div
            data-testid="app-session-topbar"
            className="relative z-50 flex h-14 flex-shrink-0 items-center gap-2 bg-[var(--background)]/95 px-4 backdrop-blur"
          >
            <button
              type="button"
              onClick={() => onSidebarOpenChange(!isSidebarOpen)}
              className="rounded-lg p-2 text-[var(--foreground-secondary)] transition-colors hover:bg-[var(--card-bg)] hover:text-[var(--foreground)]"
              aria-label={isSidebarOpen ? '关闭侧边栏' : '打开侧边栏'}
              title={isSidebarOpen ? '关闭侧边栏' : '打开侧边栏'}
            >
              <PanelLeft size={20} />
            </button>
            {showExternalLink && (
              <a
                href="https://www.ucppt.com/js"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg px-3 py-2 text-sm text-[var(--foreground-secondary)] transition-colors hover:bg-[var(--card-bg)] hover:text-[var(--foreground)]"
                title="返回 ucppt.com/js"
              >
                设计知外 ucppt.com
              </a>
            )}
          </div>
          <div
            data-testid="app-session-top-mask"
            className="pointer-events-none absolute left-0 right-0 top-14 z-40 h-8 bg-gradient-to-b from-[var(--background)] to-transparent"
          />
          <div data-testid="app-session-content" className="relative min-h-0 flex-1 flex flex-col">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
