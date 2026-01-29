'use client';

import { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { api } from '@/lib/api';
import { useAuth } from './AuthContext';

export interface Session {
  session_id: string;
  status: string;
  created_at: string;
  user_input: string;
  progress?: number;
  analysis_mode?: string;
  isTemporary?: boolean;
  session_type?: 'analysis' | 'search';
  pinned?: boolean;  // 🆕 置顶标记
}

interface SessionContextType {
  // 会话列表状态
  sessions: Session[];
  setSessions: React.Dispatch<React.SetStateAction<Session[]>>;

  // 分页状态
  currentPage: number;
  hasMorePages: boolean;
  loadingMore: boolean;
  loadMoreSessions: () => Promise<void>;
  loadMoreTriggerRef: React.RefObject<HTMLDivElement>;

  // 会话操作
  handleRenameSession: (sessionId: string) => Promise<void>;
  handlePinSession: (sessionId: string) => Promise<void>;
  handleShareSession: (sessionId: string) => void;
  handleDeleteSession: (sessionId: string) => Promise<void>;

  // 工具函数
  dedupeSessions: (sessions: Session[]) => Session[];
  refreshSessions: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMorePages, setHasMorePages] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);

  // 去重工具函数
  const dedupeSessions = useCallback((items: Session[]) => {
    const seen = new Set<string>();
    return items.filter(item => {
      if (seen.has(item.session_id)) return false;
      seen.add(item.session_id);
      return true;
    });
  }, []);

  // 刷新会话列表
  const refreshSessions = useCallback(async () => {
    if (!user) {
      setSessions([]);
      setHasMorePages(false);
      setCurrentPage(1);
      return;
    }

    try {
      const data = await api.getUnifiedSessions(1, 20);
      setSessions(dedupeSessions(data.sessions || []));
      setHasMorePages(data.has_next || false);
      setCurrentPage(1);
    } catch (err) {
      console.error('获取会话列表失败:', err);
    }
  }, [user, dedupeSessions]);

  // 加载更多会话
  const loadMoreSessions = useCallback(async () => {
    if (loadingMore || !hasMorePages) return;

    setLoadingMore(true);
    try {
      const nextPage = currentPage + 1;
      const data = await api.getUnifiedSessions(nextPage, 20);

      if (!data.sessions || data.sessions.length === 0) {
        setHasMorePages(false);
        return;
      }

      setSessions(prev => dedupeSessions([...prev, ...data.sessions]));
      setCurrentPage(nextPage);
      setHasMorePages(data.has_next || false);
    } catch (err) {
      console.error('加载更多会话失败:', err);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMorePages, currentPage, dedupeSessions]);

  // 重命名会话
  const handleRenameSession = useCallback(async (sessionId: string) => {
    const newName = prompt('请输入新的会话名称:');
    if (newName && newName.trim()) {
      try {
        await api.updateSession(sessionId, { display_name: newName.trim() });
        setSessions(prev =>
          dedupeSessions(
            prev.map(s =>
              s.session_id === sessionId ? { ...s, user_input: newName.trim() } : s
            )
          )
        );
        alert('重命名成功');
      } catch (err) {
        console.error('重命名失败:', err);
        alert('重命名失败，请重试');
      }
    }
  }, [dedupeSessions]);

  // 置顶会话（toggle逻辑）
  const handlePinSession = useCallback(async (sessionId: string) => {
    try {
      // 查找当前会话的置顶状态
      const targetSession = sessions.find(s => s.session_id === sessionId);
      if (!targetSession) {
        console.warn('⚠️ 未找到要操作的会话:', sessionId);
        return;
      }

      const newPinnedState = !targetSession.pinned;
      console.log(`🔝 ${newPinnedState ? '置顶' : '取消置顶'}会话:`, sessionId);

      const result = await api.updateSession(sessionId, { pinned: newPinnedState });
      console.log('🔝 操作API响应:', result);

      // 更新本地状态
      setSessions(prev => {
        const updated = prev.map(s =>
          s.session_id === sessionId
            ? { ...s, pinned: newPinnedState }
            : s
        );
        // 按置顶状态重新排序：置顶会话在前
        return dedupeSessions(updated.sort((a, b) => {
          if (a.pinned && !b.pinned) return -1;
          if (!a.pinned && b.pinned) return 1;
          return 0;
        }));
      });

      alert(newPinnedState ? '置顶成功' : '取消置顶成功');
    } catch (err: any) {
      console.error('❌ 操作失败:', err);
      const errorMsg = err?.response?.data?.detail || err?.message || '未知错误';
      alert(`操作失败: ${errorMsg}`);
    }
  }, [sessions, dedupeSessions]);

  // 分享会话
  const handleShareSession = useCallback((sessionId: string) => {
    const session = sessions.find(s => s.session_id === sessionId);
    const basePath = session?.session_type === 'search' ? '/search' : '/analysis';
    const link = `${window.location.origin}${basePath}/${sessionId}`;
    navigator.clipboard.writeText(link);
    alert('会话链接已复制到剪贴板');
  }, [sessions]);

  // 删除会话
  const handleDeleteSession = useCallback(async (sessionId: string) => {
    if (confirm('确定要删除这个会话吗？此操作不可恢复。')) {
      try {
        const session = sessions.find(s => s.session_id === sessionId);
        if (session?.session_type === 'search') {
          await api.deleteSearchSession(sessionId);
        } else {
          await api.deleteSession(sessionId);
        }

        // 🔥 v7.284: 直接从本地状态移除会话，避免依赖 refreshSessions
        // 这样即使 user 状态不稳定也不会导致列表清空
        setSessions(prev => prev.filter(s => s.session_id !== sessionId));
        alert('删除成功');
      } catch (err: any) {
        console.error('删除失败:', err);
        const errorMsg = err.response?.data?.detail || '删除失败，请重试';
        alert(errorMsg);
      }
    }
  }, [sessions]);

  // 初始加载会话列表
  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  // Intersection Observer 滚动加载
  useEffect(() => {
    const trigger = loadMoreTriggerRef.current;
    if (!trigger || !hasMorePages) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loadingMore && hasMorePages) {
          loadMoreSessions();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(trigger);
    return () => observer.disconnect();
  }, [loadingMore, hasMorePages, loadMoreSessions]);

  const value: SessionContextType = {
    sessions,
    setSessions,
    currentPage,
    hasMorePages,
    loadingMore,
    loadMoreSessions,
    loadMoreTriggerRef,
    handleRenameSession,
    handlePinSession,
    handleShareSession,
    handleDeleteSession,
    dedupeSessions,
    refreshSessions,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}
