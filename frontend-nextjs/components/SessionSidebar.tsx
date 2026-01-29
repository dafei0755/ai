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
  MoreVertical,
  Edit2,
  Pin,
  Share2,
  Trash2,
  Sparkles
} from 'lucide-react';

export interface Session {
  session_id: string;
  status: string;
  created_at: string;
  user_input: string;
  progress?: number;
  analysis_mode?: string;
  isTemporary?: boolean;
  session_type?: 'analysis' | 'search';  // 🆕 v7.180: 区分会话类型
  pinned?: boolean;  // 🆕 置顶标记
}

interface SessionSidebarProps {
  sessions: Session[];
  currentSessionId?: string;
  onRenameSession?: (sessionId: string) => void;
  onPinSession?: (sessionId: string) => void;
  onShareSession?: (sessionId: string) => void;
  onDeleteSession?: (sessionId: string) => void;
  // 🔥 v7.105: 滚动加载支持
  loadMoreTriggerRef?: React.RefObject<HTMLDivElement>;
}

export function SessionSidebar({
  sessions,
  currentSessionId,
  onRenameSession,
  onPinSession,
  onShareSession,
  onDeleteSession,
  loadMoreTriggerRef  // 🔥 v7.105: 滚动加载触发器
}: SessionSidebarProps) {
  const router = useRouter();
  const [menuOpenSessionId, setMenuOpenSessionId] = useState<string | null>(null);

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

  // 渲染单个会话项
  const renderSessionItem = (session: Session) => {
    const isCurrentSession = session.session_id === currentSessionId;

    return (
      <div key={`sidebar-${session.session_id}`} className="relative group">
      <button
        onClick={(e) => {
          // v7.290: 默认在新标签页打开历史记录
          let targetUrl = '';
          if (session.session_type === 'search') {
            targetUrl = `/search/${session.session_id}`;
          } else if (session.status === 'completed') {
            targetUrl = `/report/${session.session_id}`;
          } else {
            targetUrl = `/analysis/${session.session_id}`;
          }

          // 始终在新标签页打开
          window.open(targetUrl, '_blank');
        }}
        onAuxClick={(e) => {
          // v7.290: 中键点击在新标签页打开
          if (e.button === 1) {
            e.preventDefault();
            let targetUrl = '';
            if (session.session_type === 'search') {
              targetUrl = `/search/${session.session_id}`;
            } else if (session.status === 'completed') {
              targetUrl = `/report/${session.session_id}`;
            } else {
              targetUrl = `/analysis/${session.session_id}`;
            }
            window.open(targetUrl, '_blank');
          }
        }}
        className={`w-full text-sm px-3 py-2 rounded-lg transition-colors text-left ${
          isCurrentSession
            ? 'bg-[var(--card-bg)] text-[var(--foreground)] border border-blue-500/30'
            : 'text-[var(--foreground-secondary)] hover:bg-[var(--card-bg)] hover:text-[var(--foreground)]'
        }`}
      >
        <div className="flex items-center gap-2">
          <div className="flex-1 pr-6 line-clamp-2">{session.user_input || '未命名会话'}</div>
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
          {/* 🆕 v7.180: 会话类型标记 */}
          {session.session_type === 'search' && (
            <span className="text-xs text-green-500">[搜索]</span>
          )}
          {session.session_type !== 'search' && session.analysis_mode === 'deep_thinking' && (
            <span className="text-xs text-orange-500">[深度思考]</span>
          )}
          {session.session_type !== 'search' && session.analysis_mode !== 'deep_thinking' && (
            <span className="text-xs text-blue-500">[普通思考]</span>
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
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
            <Sparkles size={20} />
          </div>
          <h1 className="text-lg font-semibold text-[var(--foreground)]">方案高参</h1>
        </div>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto p-3 pb-20">
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
