// app/page.tsx
// 首页：用户输入需求并启动分析

'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Send,
  ArrowUp,
  Plus,
  PanelLeft,
  X,
  MoreVertical,
  Edit2,
  Pin,
  Share2,
  Trash2,
  Sparkles
} from 'lucide-react';
import { api } from '@/lib/api';
import { useWorkflowStore } from '@/store/useWorkflowStore';
import { UserPanel } from '@/components/layout/UserPanel';
import { useAuth } from '@/contexts/AuthContext';
import { useSession } from '@/contexts/SessionContext';
import { SessionSidebar } from '@/components/SessionSidebar';
import { deriveSessionTitle } from '@/lib/sessionTitle';
// 🔥 v7.109: 进度直接在时间戳后显示，移除了 ProgressBadge 组件
// 🔥 v7.110: 提取侧边栏为公共组件 SessionSidebar
// 🆕 v7.283: 使用全局 SessionContext 管理会话状态

export default function HomePage() {
  const router = useRouter();
  const { setSessionId, setIsLoading, isLoading, setError, error } = useWorkflowStore();
  const { user, isLoading: authLoading } = useAuth();

  // 🆕 v7.283: 使用全局会话状态
  const {
    sessions,
    setSessions,
    loadMoreTriggerRef,
    handleRenameSession,
    handlePinSession,
    handleShareSession,
    handleDeleteSession,
    dedupeSessions,
  } = useSession();

  const [userInput, setUserInput] = useState('');

  // 强制清空输入框，防止浏览器 autocomplete 恢复历史内容
  useEffect(() => {
    setUserInput('');
  }, []);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('homeSidebarOpen');
      return saved !== null ? saved === 'true' : true;
    }
    return true;
  });

  // 保存侧边栏状态到localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('homeSidebarOpen', String(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  // 🔥 检测是否在 iframe 中（用于显示主网站链接）
  const isInIframe = typeof window !== 'undefined' && window.self !== window.top;



  // 🔥 v7.283: 移除本地会话状态管理，使用全局 SessionContext

  // 🔥 v7.9.3: 日期分组函数 - 按相对时间分组会话
  const groupSessionsByDate = useCallback(
    (sessions: Array<{ session_id: string; status: string; created_at: string; user_input: string; display_name?: string; isTemporary?: boolean; session_type?: 'analysis' | 'search' }>) => {
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
      const last7Days = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
      const last30Days = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

      // 🔥 v7.106.2: 当前月份第一天，用于区分"本月其他日期"和"历史月份"
      const currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);

      const groups: {
        today: typeof sessions;
        yesterday: typeof sessions;
        last7Days: typeof sessions;
        last30Days: typeof sessions;
        byMonth: Record<string, typeof sessions>;
      } = {
        today: [],
        yesterday: [],
        last7Days: [],
        last30Days: [],
        byMonth: {}
      };

      sessions.forEach(session => {
        const sessionDate = new Date(session.created_at);
        const sessionDay = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());

        if (sessionDay.getTime() === today.getTime()) {
          groups.today.push(session);
        } else if (sessionDay.getTime() === yesterday.getTime()) {
          groups.yesterday.push(session);
        } else if (sessionDay.getTime() >= last7Days.getTime()) {
          groups.last7Days.push(session);
        } else if (sessionDay.getTime() >= last30Days.getTime() && sessionDay.getTime() >= currentMonthStart.getTime()) {
          // 🔥 v7.106.2: 只有当前月份的会话才进入"30天内"分组
          groups.last30Days.push(session);
        } else {
          // 🔥 v7.106.2: 跨月或更早的会话按月份归档
          const monthKey = `${sessionDate.getFullYear()}-${String(sessionDate.getMonth() + 1).padStart(2, '0')}`;
          if (!groups.byMonth[monthKey]) {
            groups.byMonth[monthKey] = [];
          }
          groups.byMonth[monthKey].push(session);
        }
      });

      return groups;
    },
    []
  );

  // 🔥 v7.283: 移除本地会话加载逻辑，使用全局 SessionContext

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 验证逻辑：必须输入文字描述（文件作为辅助材料）
    if (!userInput.trim()) {
      setError('请输入文字描述您的需求');
      return;
    }

    setIsLoading(true);
    setError(null);

    // 🔥 乐观更新：立即创建临时会话记录
    const tempSessionId = `temp-${Date.now()}`;
    const displayText = userInput.trim();
    const displayTitle = deriveSessionTitle(displayText);
    const tempSession = {
      session_id: tempSessionId,
      status: 'initializing',
      created_at: new Date().toISOString(),
      user_input: displayText,
      display_name: displayTitle,
      isTemporary: true // 标记为临时记录
    };

    // 立即添加到会话列表顶部
    setSessions(prevSessions => dedupeSessions([tempSession, ...prevSessions]));

    try {
      console.log('🚀 提交分析请求', { userInput: userInput.trim() });

      const response = await api.sendConversationMessage('', userInput.trim());

      console.log('✅ 对话态会话创建成功', response);

      // 用真实会话替换临时记录
      setSessions(prevSessions =>
        prevSessions.map(s =>
          s.session_id === tempSessionId
            ? {
                session_id: response.session_id,
                status: 'conversation_active',
                created_at: new Date().toISOString(),
                user_input: displayText,
                display_name: displayTitle,
                isTemporary: false
              } // 替换为真实数据
            : s
        )
      );
      void api.updateSession(response.session_id, { display_name: displayTitle }).catch((error) => {
        console.warn('[home] persist conversation title failed:', error);
      });

      setSessionId(response.session_id);

      // 首页的第一条对话写入 sessionStorage，供分析页预填充
      if (response.session_id && response.reply) {
        sessionStorage.setItem(
          `conv_init_${response.session_id}`,
          JSON.stringify({
            userMessage: displayText,
            aiReply: response.reply,
            guidance_card: response.guidance_card ?? null,
          })
        );
      }

      // 🔥 清空输入
      setUserInput('');

      router.push(`/analysis/${response.session_id}`);

    } catch (error: any) {
      console.error('Start analysis failed:', error);
      const networkMessage =
        error?.message?.includes('Network Error') || error?.code === 'ERR_NETWORK'
          ? '后端连接失败：请确认 FastAPI 后端已启动。浏览器仍访问 3001，后端端口由启动脚本和 Next 代理管理。'
          : error?.response?.data?.detail || error?.message || '创建对话会话失败，请重试';
      setError(networkMessage);

      // 失败时移除临时记录
      setSessions(prevSessions =>
        prevSessions.filter(s => s.session_id !== tempSessionId)
      );
    } finally {
      setIsLoading(false);
    }
  };

  // 🔥 v7.283: 移除本地会话操作函数，使用全局 SessionContext

  // 本地开发阶段允许未登录进入首页；正式独立用户系统上线后再收紧入口权限。

  // 🔒 认证加载中，显示加载状态
  if (authLoading) {
    return (
      <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-gray-500" />
          <p className="text-[var(--foreground-secondary)]">正在验证身份...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ucppt-advisor-shell flex flex-col h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden relative">
      <div className="flex flex-1 overflow-hidden relative">
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* 侧边栏 - 使用公共组件 SessionSidebar */}
      <div
        className={`${
          isSidebarOpen ? 'w-[310px] translate-x-0' : 'w-0 -translate-x-full md:translate-x-0 md:w-0'
        } bg-[var(--sidebar-bg)] border-r border-[var(--border-color)] transition-all duration-300 ease-in-out flex flex-col fixed md:relative h-full z-40 overflow-hidden`}
      >
        {isSidebarOpen && (
          <>
            <div className="min-w-[310px] pt-4 h-0" />
            <div className="flex-1 flex flex-col min-h-0">
              <SessionSidebar
                sessions={sessions}
                onRenameSession={handleRenameSession}
                onPinSession={handlePinSession}
                onShareSession={handleShareSession}
                onDeleteSession={handleDeleteSession}
                loadMoreTriggerRef={loadMoreTriggerRef}
              />
            </div>

            {/* 底部用户面板 - 固定在底部 */}
            <div className="border-t border-[var(--border-color)] min-w-[310px] flex-shrink-0">
              <div className="p-3">
                <UserPanel />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative w-full">
        {/* Header / Toggle */}
        <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] rounded-lg transition-colors"
            title={isSidebarOpen ? "关闭侧边栏" : "打开侧边栏"}
          >
            <PanelLeft size={20} />
          </button>

          {/* 🔗 跳转到主网站链接（独立模式专用） */}
          {!isInIframe && (
            <a
              href="https://www.ucppt.com/js"
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-2 text-sm text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] rounded-lg transition-colors flex items-center gap-1"
              title="返回 ucppt.com/js"
            >
              <span>设计知外 ucppt.com</span>
              <svg
                className="w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
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

        <div
          className="flex-1 flex flex-col items-center justify-center py-8 px-4 sm:px-8"
          onMouseDown={(e) => {
            // 🆕 v7.242: 阻止点击空白区域时触发 textarea 焦点
            if (e.target === e.currentTarget) {
              e.preventDefault();
            }
          }}
        >
          <div
            className="advisor-chat-column w-full space-y-8"
            onMouseDown={(e) => {
              // 🆕 v7.242: 阻止点击空白区域时触发 textarea 焦点
              if (e.target === e.currentTarget) {
                e.preventDefault();
              }
            }}
          >
            {/* Hero Section */}
            <div className="text-center space-y-3">
              <div className="flex items-center justify-center gap-2 mb-6">
                <div className="w-8 h-8 rounded-lg ucppt-icon-brand">
                  <Sparkles size={20} />
                </div>
                <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--foreground)]">
                  方案高参
                </h1>
              </div>
            </div>

            {/* Input Composer */}
            <form onSubmit={handleSubmit} autoComplete="off" className="relative overflow-hidden rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] shadow-xl">
              {/* Textarea */}
              <div>
                  <textarea
                    ref={(el) => {
                      // 在 DOM 挂载时直接清空 DOM value，防止浏览器 autocomplete 填充
                      if (el) el.value = userInput;
                    }}
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    placeholder="输入你的想法、问题或设计需求，先做需求重构..."
                    className="w-full bg-inherit text-[var(--foreground)] text-base leading-6 px-6 pt-6 pb-6 min-h-[170px] outline-none resize-none placeholder:text-[var(--foreground-secondary)]"
                    disabled={isLoading}
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck={false}
                  />
                </div>

                <div className="flex items-center justify-between pl-3 pr-5 py-3 border-t border-[var(--border-color)] rounded-b-xl bg-[var(--card-bg)]">
                  <div className="flex gap-2 text-[var(--foreground-secondary)]">
                    <span
                      className={`px-3 py-1.5 text-xs font-medium rounded-full text-white shadow-sm whitespace-nowrap ${
                        isLoading ? 'bg-blue-500' : 'bg-gradient-to-r from-blue-500 to-cyan-500'
                      }`}
                      aria-live="polite"
                    >
                      {isLoading ? '正在创建会话...' : '开始需求重构'}
                    </span>
                  </div>
                  {/* 发送按钮 */}
                  <button
                    type="submit"
                    disabled={isLoading || !userInput.trim()}
                    aria-label={isLoading ? '正在创建会话' : '发送'}
                    className={`
                      p-2.5 rounded-full transition-all duration-300
                      ${userInput.trim()
                        ? 'bg-blue-500 text-white hover:bg-blue-600 hover:scale-105 shadow-lg'
                        : 'bg-[#3b3b3d] text-[var(--foreground-secondary)] cursor-not-allowed'}
                    `}
                    title={
                      isLoading 
                        ? '正在分析中... 预计12-60秒（取决于需求复杂度）'
                        : userInput.trim() 
                          ? '发送' 
                          : '请输入文字描述您的需求'
                    }
                  >
                    {isLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <ArrowUp className="w-5 h-5" />
                    )}
                  </button>
                </div>
            </form>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-red-900/20 border border-red-900/50 rounded-lg text-red-400 text-sm text-center">
                {error}
              </div>
            )}

          </div>
        </div>
      </div>

      </div>{/* end flex-1 wrapper */}
    </div>
  );
}
