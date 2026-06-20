/**
 * SessionSidebar - 会话历史侧边栏公共组件
 *
 * 用于显示用户的历史会话列表，支持：
 * - 按日期分组（今天/昨天/7天内/30天内/按月份）
 * - 进度显示（运行中/失败/拒绝状态）
 * - 分析模式标签（深度思考）
 * - 会话操作（重命名/置顶/分享/删除）
 */

'use client';

import { useMemo, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Plus,
  Search,
  MessageCircle,
  X,
  MoreVertical,
  Edit2,
  Pin,
  Share2,
  Trash2,
  Sparkles
} from 'lucide-react';
import { resolveSessionTitle } from '@/lib/sessionTitle';

export interface Session {
  session_id: string;
  status: string;
  created_at: string;
  user_input: string;
  display_name?: string;
  progress?: number;
  analysis_mode?: string;
  isTemporary?: boolean;
  session_type?: 'analysis' | 'search';  // 🆕 v7.180: 区分会话类型
  pinned?: boolean;  // 🆕 置顶标记
  is_demo?: boolean; // 🎭 演示样例会话标记
}

interface SessionSidebarProps {
  sessions: Session[];
  currentSessionId?: string;
  navigationMode?: 'new-tab' | 'in-place';
  onRenameSession?: (sessionId: string) => void;
  onPinSession?: (sessionId: string) => void;
  onShareSession?: (sessionId: string) => void;
  onDeleteSession?: (sessionId: string) => void;
  // 🔥 v7.105: 滚动加载支持
  loadMoreTriggerRef?: React.RefObject<HTMLDivElement | null>;
}

export function SessionSidebar({
  sessions,
  currentSessionId,
  navigationMode = 'new-tab',
  onRenameSession,
  onPinSession,
  onShareSession,
  onDeleteSession,
  loadMoreTriggerRef  // 🔥 v7.105: 滚动加载触发器
}: SessionSidebarProps) {
  const router = useRouter();
  const [menuOpenSessionId, setMenuOpenSessionId] = useState<string | null>(null);
  const [isHistorySearchOpen, setIsHistorySearchOpen] = useState(false);
  const [historySearchQuery, setHistorySearchQuery] = useState('');

  // 去重工具：避免重复 session_id 导致 React key 警告
  const dedupeSessions = useCallback((items: Session[]) => {
    const seen = new Set<string>();
    return items.filter(item => {
      if (seen.has(item.session_id)) return false;
      seen.add(item.session_id);
      return true;
    });
  }, []);

  const uniqueSessions = useMemo(() => dedupeSessions(sessions), [sessions, dedupeSessions]);

  // 日期分组函数 - 按相对时间分组会话
  const groupSessionsByDate = useCallback((sessions: Session[]) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const last7Days = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    const last30Days = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

    const groups: {
      today: Session[];
      yesterday: Session[];
      last7Days: Session[];
      last30Days: Session[];
      byMonth: Record<string, Session[]>;
    } = {
      today: [],
      yesterday: [],
      last7Days: [],
      last30Days: [],
      byMonth: {}
    };

    // 🆕 按置顶状态排序：置顶会话在前
    const sortedSessions = [...sessions].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return 0;
    });

    sortedSessions.forEach(session => {
      const sessionDate = new Date(session.created_at);
      const sessionDay = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());

      if (sessionDay.getTime() === today.getTime()) {
        groups.today.push(session);
      } else if (sessionDay.getTime() === yesterday.getTime()) {
        groups.yesterday.push(session);
      } else if (sessionDay.getTime() >= last7Days.getTime()) {
        groups.last7Days.push(session);
      } else if (sessionDay.getTime() >= last30Days.getTime()) {
        groups.last30Days.push(session);
      } else {
        const monthKey = `${sessionDate.getFullYear()}-${String(sessionDate.getMonth() + 1).padStart(2, '0')}`;
        if (!groups.byMonth[monthKey]) {
          groups.byMonth[monthKey] = [];
        }
        groups.byMonth[monthKey].push(session);
      }
    });

    return groups;
  }, []);

  const groupedSessions = useMemo(() => groupSessionsByDate(uniqueSessions), [uniqueSessions, groupSessionsByDate]);

  const getSessionTargetUrl = useCallback((session: Session) => {
    if (session.session_type === 'search') {
      return `/search/${session.session_id}`;
    }

    if (navigationMode === 'in-place') {
      return `/analysis/${session.session_id}`;
    }

    if (session.status === 'completed') {
      return `/report/${session.session_id}`;
    }

    return `/analysis/${session.session_id}`;
  }, [navigationMode]);

  const navigateToSession = useCallback((session: Session) => {
    const targetUrl = getSessionTargetUrl(session);
    if (navigationMode === 'in-place') {
      router.push(targetUrl);
      return;
    }

    window.open(targetUrl, '_blank');
  }, [getSessionTargetUrl, navigationMode, router]);

  const historySearchResults = useMemo(() => {
    const query = historySearchQuery.trim().toLowerCase();
    const searchableSessions = uniqueSessions.filter(session => !session.is_demo);

    if (!query) {
      return searchableSessions.slice(0, 30);
    }

    return searchableSessions
      .filter(session => {
        const title = resolveSessionTitle(session.user_input || '', session.display_name);
        return `${title} ${session.user_input} ${session.display_name ?? ''}`.toLowerCase().includes(query);
      })
      .slice(0, 30);
  }, [historySearchQuery, uniqueSessions]);

  // 格式化月份显示（"2025-11" -> "2025年11月" 或 "11月"）
  const formatMonthLabel = (monthKey: string) => {
    const [year, month] = monthKey.split('-');
    const currentYear = new Date().getFullYear().toString();

    if (year === currentYear) {
      return `${parseInt(month)}月`;
    } else {
      return `${year}年${parseInt(month)}月`;
    }
  };

  const quickActionClass =
    'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-[var(--foreground-secondary)] transition-colors hover:bg-[var(--card-bg)] hover:text-[var(--foreground)]';

  // 渲染单个会话项
  const renderSessionItem = (session: Session) => {
    const isCurrentSession = session.session_id === currentSessionId;
    const displayTitle = resolveSessionTitle(session.user_input || '', session.display_name);

    return (
      <div key={`sidebar-${session.session_id}`} className="relative group">
      <button
        onClick={(e) => {
          // 🎭 Demo 会话不可点击，仅作为展示参考
          if (session.is_demo) return;

          navigateToSession(session);
        }}
        onAuxClick={(e) => {
          if (session.is_demo) return;
          // v7.290: 中键点击在新标签页打开
          if (e.button === 1) {
            e.preventDefault();
            window.open(getSessionTargetUrl(session), '_blank');
          }
        }}
        title={session.is_demo ? '演示样例，不可点击' : (session.display_name || session.user_input)}
        className={`w-full text-sm px-3 py-2 rounded-lg transition-colors text-left ${
          session.is_demo
            ? 'opacity-60 cursor-default text-[var(--foreground-secondary)]'
            : isCurrentSession
              ? 'bg-[var(--card-bg)] text-[var(--foreground)] border border-blue-500/30'
              : 'text-[var(--foreground-secondary)] hover:bg-[var(--card-bg)] hover:text-[var(--foreground)]'
        }`}
      >
        <div className="flex items-center gap-2">
          {session.is_demo && (
            <span className="shrink-0 text-[10px] px-1 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30 leading-none">
              示例
            </span>
          )}
          <div className="flex-1 pr-6 line-clamp-1 text-[var(--foreground)]">{displayTitle || '未命名会话'}</div>
        </div>

        <div className="flex items-center gap-1.5 mt-1">
          <div className="text-xs text-gray-500">
            {new Date(session.created_at).toLocaleString('zh-CN', {
              month: 'numeric',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
            {session.progress !== undefined &&
             ['running', 'failed', 'rejected'].includes(session.status) && (
              <span className={
                session.status === 'running' ? 'text-blue-400' :
                session.status === 'failed' ? 'text-red-400' :
                'text-yellow-400'
              }>
                {' '}({Math.round(session.progress * 100)}%)
              </span>
            )}
          </div>
          {/* 🆕 置顶图标 - 放在时间戳后面 */}
          {session.pinned && (
            <Pin size={12} className="text-yellow-500 flex-shrink-0" fill="currentColor" />
          )}
        </div>
      </button>

      <button
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpenSessionId(menuOpenSessionId === session.session_id ? null : session.session_id);
        }}
        className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-[var(--sidebar-bg)] rounded transition-opacity"
      >
        <MoreVertical size={16} />
      </button>

      {menuOpenSessionId === session.session_id && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setMenuOpenSessionId(null)} />
          <div className="absolute right-0 top-8 z-20 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg py-1 min-w-[140px]">
            <button
              onClick={() => {
                onRenameSession?.(session.session_id);
                setMenuOpenSessionId(null);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left"
            >
              <Edit2 size={14} />
              <span>重命名</span>
            </button>
            <button
              onClick={() => {
                onPinSession?.(session.session_id);
                setMenuOpenSessionId(null);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left"
            >
              <Pin size={14} className={session.pinned ? 'fill-yellow-500 text-yellow-500' : ''} />
              <span>{session.pinned ? '取消置顶' : '置顶'}</span>
            </button>
            <button
              onClick={() => {
                onShareSession?.(session.session_id);
                setMenuOpenSessionId(null);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left"
            >
              <Share2 size={14} />
              <span>分享</span>
            </button>
            <div className="border-t border-[var(--border-color)] my-1" />
            <button
              onClick={() => {
                onDeleteSession?.(session.session_id);
                setMenuOpenSessionId(null);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-900/20 text-red-400 transition-colors text-left"
            >
              <Trash2 size={14} />
              <span>删除</span>
            </button>
          </div>
        </>
      )}
    </div>
    );
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Logo 和标题 - v7.105.2: 调整padding与右侧header对齐 */}
      <div className="px-3 py-3 border-b border-[var(--border-color)] flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg ucppt-icon-brand">
            <Sparkles size={20} />
          </div>
          <h1 className="text-lg font-semibold text-[var(--foreground)]">方案高参</h1>
        </div>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto p-3 pb-20">
        <div className="mb-3 space-y-1">
          <button
            type="button"
            onClick={() => router.push('/')}
            className={quickActionClass}
          >
            <Plus size={16} className="shrink-0" />
            <span>新对话</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setHistorySearchQuery('');
              setIsHistorySearchOpen(true);
            }}
            className={quickActionClass}
          >
            <Search size={16} className="shrink-0" />
            <span>搜索对话</span>
          </button>
        </div>

        {isHistorySearchOpen && (
          <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 px-4 pt-[18vh]">
            <div
              role="dialog"
              aria-label="搜索对话"
              className="w-full max-w-[680px] overflow-hidden rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] shadow-2xl"
            >
              <div className="flex items-center gap-3 border-b border-[var(--border-color)] px-4 py-3">
                <Search size={18} className="shrink-0 text-[var(--foreground-secondary)]" />
                <input
                  value={historySearchQuery}
                  onChange={(event) => setHistorySearchQuery(event.target.value)}
                  placeholder="搜索对话..."
                  autoFocus
                  className="min-w-0 flex-1 bg-transparent text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--foreground-secondary)]"
                />
                <button
                  type="button"
                  onClick={() => setIsHistorySearchOpen(false)}
                  className="rounded-md p-1 text-[var(--foreground-secondary)] transition-colors hover:bg-[var(--sidebar-bg)] hover:text-[var(--foreground)]"
                  aria-label="关闭搜索对话"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="max-h-[420px] overflow-y-auto p-3">
                {historySearchResults.length > 0 ? (
                  <div className="space-y-1">
                    {historySearchResults.map(session => {
                      const displayTitle = resolveSessionTitle(session.user_input || '', session.display_name);
                      return (
                        <button
                          key={`history-search-${session.session_id}`}
                          type="button"
                          onClick={() => {
                            setIsHistorySearchOpen(false);
                            navigateToSession(session);
                          }}
                          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-[var(--foreground-secondary)] transition-colors hover:bg-[var(--sidebar-bg)] hover:text-[var(--foreground)]"
                        >
                          <MessageCircle size={16} className="shrink-0" />
                          <span className="min-w-0 flex-1 truncate">{displayTitle || '未命名会话'}</span>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div className="px-3 py-8 text-center text-sm text-[var(--foreground-secondary)]">
                    未找到匹配的对话
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 今天 */}
        {groupedSessions.today.length > 0 && (
          <div className="mb-4">
            <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">今天</div>
            {groupedSessions.today.map(renderSessionItem)}
          </div>
        )}

        {/* 昨天 */}
        {groupedSessions.yesterday.length > 0 && (
          <div className="mb-4">
            <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">昨天</div>
            {groupedSessions.yesterday.map(renderSessionItem)}
          </div>
        )}

        {/* 7天内 */}
        {groupedSessions.last7Days.length > 0 && (
          <div className="mb-4">
            <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">7天内</div>
            {groupedSessions.last7Days.map(renderSessionItem)}
          </div>
        )}

        {/* 30天内 */}
        {groupedSessions.last30Days.length > 0 && (
          <div className="mb-4">
            <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">30天内</div>
            {groupedSessions.last30Days.map(renderSessionItem)}
          </div>
        )}

        {/* 按月份分组 */}
        {Object.keys(groupedSessions.byMonth).sort().reverse().map(monthKey => {
          const monthSessions = groupedSessions.byMonth[monthKey];
          if (monthSessions.length === 0) return null;
          return (
            <div key={monthKey} className="mb-4">
              <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">
                {formatMonthLabel(monthKey)}
              </div>
              {monthSessions.map(renderSessionItem)}
            </div>
          );
        })}

        {/* 🔥 v7.105.3: Intersection Observer 滚动加载触发器 - 条件渲染 */}
        {loadMoreTriggerRef && (
          <div
            ref={loadMoreTriggerRef}
            className="h-1 w-full opacity-0"
            aria-hidden="true"
            data-trigger="scroll-load"
          />
        )}
      </div>
    </div>
  );
}
