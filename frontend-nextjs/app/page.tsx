// app/page.tsx
// 首页：用户输入需求并启动分析

'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Send,
  Plus,
  PanelLeft,
  X,
  MoreVertical,
  Edit2,
  Pin,
  Share2,
  Trash2,
  Paperclip,
  File,
  FileText,
  Image as ImageIcon
} from 'lucide-react';
import { api } from '@/lib/api';
import { useWorkflowStore } from '@/store/useWorkflowStore';
import { formatFileSize } from '@/lib/formatters';
import { UserPanel } from '@/components/layout/UserPanel';
import { useAuth } from '@/contexts/AuthContext';
import { SessionSidebar } from '@/components/SessionSidebar';
// 🔥 v7.109: 进度直接在时间戳后显示，移除了 ProgressBadge 组件
// 🔥 v7.110: 提取侧边栏为公共组件 SessionSidebar

export default function HomePage() {
  const router = useRouter();
  const { setSessionId, setIsLoading, isLoading, setError, error } = useWorkflowStore();
  const { user, isLoading: authLoading } = useAuth(); // 🆕 获取认证状态
  const [userInput, setUserInput] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  // 🔥 v7.107: 分析模式状态
  const [analysisMode, setAnalysisMode] = useState<'normal' | 'deep_thinking'>('normal');

  // 🔥 检测是否在 iframe 中（用于显示主网站链接）
  const isInIframe = typeof window !== 'undefined' && window.self !== window.top;

  // 🔥 已移除：之前的自动重定向逻辑（v3.0.8改为显示登录提示界面）

  // 🔥 新增：文件上传相关状态
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 🔥 Phase 3: 上传进度和预览
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // 历史会话列表
  const [sessions, setSessions] = useState<Array<{ session_id: string; status: string; created_at: string; user_input: string; isTemporary?: boolean }>>([]);
  const [currentPage, setCurrentPage] = useState(1); // 🔥 当前页码
  const [hasMorePages, setHasMorePages] = useState(false); // 🔥 是否还有更多页
  const [loadingMore, setLoadingMore] = useState(false); // 🔥 加载更多状态
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null); // 🔥 v7.105: Intersection Observer 触发器

  // 去重工具：避免重复 session_id 导致 React key 警告
  const dedupeSessions = useCallback(
    (items: Array<{ session_id: string; status: string; created_at: string; user_input: string; isTemporary?: boolean }>) => {
      const seen = new Set<string>();
      return items.filter(item => {
        if (seen.has(item.session_id)) return false;
        seen.add(item.session_id);
        return true;
      });
    },
    []
  );

  // 渲染时使用去重后的列表，避免重复 key
  const uniqueSessions = useMemo(() => dedupeSessions(sessions), [sessions, dedupeSessions]);

  // 🔥 v7.9.3: 日期分组函数 - 按相对时间分组会话
  const groupSessionsByDate = useCallback(
    (sessions: Array<{ session_id: string; status: string; created_at: string; user_input: string; isTemporary?: boolean }>) => {
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

  // 🔥 v7.9.3: 使用分组后的会话
  const groupedSessions = useMemo(() => groupSessionsByDate(uniqueSessions), [uniqueSessions, groupSessionsByDate]);

  // 会话菜单状态
  const [menuOpenSessionId, setMenuOpenSessionId] = useState<string | null>(null);

  // 🔥 v7.108: 加载更多会话（服务端分页）
  const loadMoreSessions = useCallback(async () => {
    if (loadingMore || !hasMorePages) return;

    setLoadingMore(true);
    try {
      const nextPage = currentPage + 1;
      const data = await api.getSessions(nextPage, 20, true);

      // 🔥 v7.105.5: 空数据保护 - 如果返回空数据，停止加载
      if (!data.sessions || data.sessions.length === 0) {
        console.log('[HomePage] ⏹️ 返回空数据，停止加载');
        setHasMorePages(false);
        return;
      }

      // 追加新会话到现有列表（在回调中使用dedupeSessions避免依赖）
      setSessions(prev => {
        const seen = new Set<string>();
        const merged = [...prev, ...(data.sessions || [])].filter(item => {
          if (seen.has(item.session_id)) return false;
          seen.add(item.session_id);
          return true;
        });
        
        // 🔥 v7.105.8: 移除错误的去重终止逻辑 - 应该依赖API返回的has_next
        // ❌ 之前：if (merged.length === prev.length) setHasMorePages(false);
        // ✅ 现在：只依赖API返回的has_next标志
        console.log(`[HomePage] 📊 合并结果 | prev=${prev.length} + new=${data.sessions?.length} → merged=${merged.length}`);
        
        return merged;
      });
      setCurrentPage(nextPage);
      setHasMorePages(data.has_next || false);
    } catch (err) {
      console.error('加载更多会话失败:', err);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMorePages, currentPage]);

  // 🔥 v7.105.3: Intersection Observer 滚动加载（优化无限触发问题）
  useEffect(() => {
    const trigger = loadMoreTriggerRef.current;
    if (!trigger) return;

    // 🔥 v7.105.3: 没有更多页时不监听，避免无限触发
    if (!hasMorePages) {
      console.log('[HomePage] ⏹️ 已加载全部会话，停止监听');
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        // 当触发器元素可见 且 不在加载中 且 还有更多页时，触发加载
        if (entries[0].isIntersecting && !loadingMore && hasMorePages) {
          console.log(`[HomePage] 🔄 触发滚动加载 | 当前页: ${currentPage} | 已加载: ${sessions.length}条`);
          loadMoreSessions();
        }
      },
      { threshold: 0.1 } // 触发器10%可见时触发
    );

    observer.observe(trigger);
    return () => observer.disconnect();
  }, [loadingMore, hasMorePages, loadMoreSessions, currentPage]);

  // 加载历史会话列表（仅在已登录时）
  useEffect(() => {
    // 🔒 安全检查：只有已登录用户才能获取会话列表
    if (!user) {
      console.log('[HomePage] 用户未登录，清空会话列表');
      setSessions([]);
      setHasMorePages(false);
      setCurrentPage(1);
      return;
    }

    const fetchSessions = async () => {
      try {
        // ✅ v7.108: 使用分页API（初始加载前20个，避免一次性加载所有数据）
        console.log('[HomePage] 开始加载会话列表...');
        const data = await api.getSessions(1, 20, true);
        console.log(`[HomePage] 加载完成: ${data.sessions.length} 个会话`);
        setSessions(dedupeSessions(data.sessions || []));
        setHasMorePages(data.has_next || false);
        setCurrentPage(1);
      } catch (err) {
        console.error('获取会话列表失败:', err);
      }
    };

    fetchSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]); // 🔒 只依赖user，登录状态变化时重新获取

  // 🔥 新增：文件选择处理
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      addFiles(newFiles);
    }
  };

  // 🔥 新增：拖拽上传处理
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      addFiles(newFiles);
    }
  };

  // 🔥 新增：添加文件（带验证）
  const addFiles = (newFiles: File[]) => {
    const validFiles = newFiles.filter(file => {
      // 验证文件类型
      const validTypes = [
        'application/pdf',
        'text/plain',
        'image/png',
        'image/jpeg',
        'image/jpg',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'       // .xlsx
      ];

      if (!validTypes.includes(file.type)) {
        alert(`不支持的文件类型: ${file.name}`);
        return false;
      }

      // 验证文件大小 (10MB)
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        alert(`文件过大: ${file.name} (最大10MB)`);
        return false;
      }

      return true;
    });

    setUploadedFiles(prev => [...prev, ...validFiles]);
  };

  // 🔥 新增：移除文件
  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // 🔥 新增：获取文件图标
  const getFileIcon = (file: File) => {
    if (file.type === 'application/pdf') return <File className="w-4 h-4 text-red-500" />;
    if (file.type === 'text/plain') return <FileText className="w-4 h-4 text-blue-500" />;
    if (file.type.startsWith('image/')) return <ImageIcon className="w-4 h-4 text-green-500" />;
    if (file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
      return <FileText className="w-4 h-4 text-blue-600" />;
    if (file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
      return <File className="w-4 h-4 text-green-600" />;
    return <File className="w-4 h-4 text-gray-500" />;
  };

  // 🔥 v7.6: formatFileSize 移至 lib/formatters.ts

  // 🔥 Phase 3: 预览文件
  const handlePreviewFile = (file: File) => {
    setPreviewFile(file);

    // 生成预览URL
    if (file.type.startsWith('image/')) {
      // 图片预览
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else if (file.type === 'application/pdf') {
      // PDF预览
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      // 其他文件类型显示基本信息
      setPreviewUrl(null);
    }
  };

  // 🔥 Phase 3: 关闭预览
  const handleClosePreview = () => {
    setPreviewFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  // 清理预览URL
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

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
    const displayText = userInput.trim() || `上传了 ${uploadedFiles.length} 个文件`;
    const tempSession = {
      session_id: tempSessionId,
      status: 'initializing',
      created_at: new Date().toISOString(),
      user_input: displayText,
      isTemporary: true // 标记为临时记录
    };

    // 立即添加到会话列表顶部
    setSessions(prevSessions => dedupeSessions([tempSession, ...prevSessions]));

    try {
      console.log('🚀 提交分析请求', {
        userInput: userInput.trim(),
        filesCount: uploadedFiles.length
      });

      let response;

      // 🔥 根据是否有文件选择不同的API
      if (uploadedFiles.length > 0) {
        // 使用 FormData 上传文件
        const formData = new FormData();
        formData.append('user_input', userInput.trim());
        formData.append('user_id', 'web_user');
        formData.append('analysis_mode', analysisMode);  // 🆕 v7.107

        uploadedFiles.forEach(file => {
          formData.append('files', file);
        });

        // 🔥 Phase 3: 传入进度回调
        response = await api.startAnalysisWithFiles(formData, (progress) => {
          setUploadProgress(progress);
        });
      } else {
        // 纯文本请求
        response = await api.startAnalysis({
          user_id: 'web_user',
          user_input: userInput.trim(),
          analysis_mode: analysisMode,  // 🆕 v7.107
        });
      }

      console.log('✅ 分析请求成功', response);

      // 用真实会话替换临时记录
      setSessions(prevSessions =>
        prevSessions.map(s =>
          s.session_id === tempSessionId
            ? { 
                session_id: response.session_id,
                status: response.status,
                created_at: new Date().toISOString(),
                user_input: displayText,
                isTemporary: false 
              } // 替换为真实数据
            : s
        )
      );

      setSessionId(response.session_id);

      // 🔥 清空输入和文件
      setUserInput('');
      setUploadedFiles([]);

      router.push(`/analysis/${response.session_id}`);
    } catch (error: any) {
      console.error('Start analysis failed:', error);
      setError(error.response?.data?.detail || '启动分析失败，请重试');

      // 失败时移除临时记录
      setSessions(prevSessions =>
        prevSessions.filter(s => s.session_id !== tempSessionId)
      );
    } finally {
      setIsLoading(false);
    }
  };

  // 会话菜单操作
  const handleRenameSession = async (sessionId: string) => {
    const newName = prompt('请输入新的会话名称:');
    if (newName && newName.trim()) {
      try {
        await api.updateSession(sessionId, { display_name: newName.trim() });
        // 更新本地会话列表
        setSessions(prevSessions =>
          prevSessions.map(s =>
            s.session_id === sessionId
              ? { ...s, user_input: newName.trim() }
              : s
          )
        );
        alert('重命名成功');
      } catch (err) {
        console.error('重命名失败:', err);
        alert('重命名失败，请重试');
      }
    }
    setMenuOpenSessionId(null);
  };

  const handlePinSession = async (sessionId: string) => {
    try {
      await api.updateSession(sessionId, { pinned: true });
      // 更新本地会话列表 - 将置顶的会话移到最前面
      setSessions(prevSessions => {
        const targetSession = prevSessions.find(s => s.session_id === sessionId);
        if (!targetSession) return prevSessions;

        const otherSessions = prevSessions.filter(s => s.session_id !== sessionId);
        return [targetSession, ...otherSessions];
      });
      alert('置顶成功');
    } catch (err) {
      console.error('置顶失败:', err);
      alert('置顶失败，请重试');
    }
    setMenuOpenSessionId(null);
  };

  const handleShareSession = (sessionId: string) => {
    // 复制会话链接
    const link = `${window.location.origin}/analysis/${sessionId}`;
    navigator.clipboard.writeText(link);
    alert('会话链接已复制到剪贴板');
    setMenuOpenSessionId(null);
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (confirm('确定要删除这个会话吗？此操作不可恢复。')) {
      try {
        await api.deleteSession(sessionId);
        // 🆕 v7.106: 强制刷新列表（重新调用API，确保与后端一致）
        try {
          const data = await api.getSessions(currentPage, 20, true);
          setSessions(dedupeSessions(data.sessions || []));
          setHasMorePages(data.has_next || false);
        } catch (refreshErr) {
          console.error('刷新会话列表失败:', refreshErr);
          // 回退到本地过滤
          setSessions(prevSessions => prevSessions.filter(s => s.session_id !== sessionId));
        }
        alert('删除成功');
      } catch (err: any) {
        console.error('删除失败:', err);
        // 显示更友好的错误信息
        const errorMsg = err.response?.data?.detail || '删除失败，请重试';
        alert(errorMsg);
      }
      setMenuOpenSessionId(null);
    }
  };

  // 🎯 v3.0.15: 未登录时显示简化登录界面
  // 应用内部处理登录检测，显示"立即登录"按钮
  if (!authLoading && !user) {
    return (
      <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] items-center justify-center p-4 relative">
        {/* 🔗 左上角跳转到主网站链接 */}
        <div className="absolute top-4 left-4 z-10">
          <a
            href="https://www.ucppt.com/js"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-2 text-sm text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] rounded-lg transition-colors flex items-center gap-1"
            title="返回 ucppt.com/js"
          >
            <span>返回网站</span>
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
        </div>

        <div className="max-w-md w-full space-y-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-6">
            <div className="w-12 h-12 bg-gray-600 dark:bg-gray-700 rounded-lg flex items-center justify-center text-white text-2xl">
              AI
            </div>
          </div>
          <h1 className="text-2xl font-semibold text-[var(--foreground)]">
            方案高参
          </h1>

          {/* 🎯 v3.0.15: 简化登录界面 - 只有一个"立即登录"按钮 */}
          <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6 space-y-4">
            <div className="text-lg text-[var(--foreground-secondary)] mb-4">
              请先登录以使用应用
            </div>

            <button
              onClick={() => {
                // 🎯 新架构：跳转到宣传页面（包含WPCOM隐藏区块的应用入口）
                // 用户在宣传页面登录后，会看到应用入口链接，点击即可进入应用
                window.location.href = 'https://www.ucppt.com/js';
              }}
              className="w-full px-6 py-3 bg-gray-700 dark:bg-gray-600 hover:bg-gray-600 dark:hover:bg-gray-500 text-white font-medium rounded-lg transition-all"
            >
              前往登录
            </button>

            <div className="text-xs text-[var(--foreground-secondary)]">
              登录后在网站页面中找到应用入口
            </div>
          </div>

          <div className="text-sm text-[var(--foreground-secondary)]">
            ucppt.com
          </div>
        </div>
      </div>
    );
  }

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
    <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden relative">
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
          isSidebarOpen ? 'w-[260px] translate-x-0' : 'w-0 -translate-x-full md:translate-x-0 md:w-0'
        } bg-[var(--sidebar-bg)] border-r border-[var(--border-color)] transition-all duration-300 ease-in-out flex flex-col fixed md:relative h-full z-40 overflow-hidden`}
      >
        {isSidebarOpen && (
          <>
            <div className="min-w-[260px] pt-16 h-0" />
            <div className="flex-1 flex flex-col min-h-0">
              <SessionSidebar
                sessions={sessions}
                showNewButton={true}
                onNewSession={() => window.location.reload()}
                onRenameSession={handleRenameSession}
                onPinSession={handlePinSession}
                onShareSession={handleShareSession}
                onDeleteSession={handleDeleteSession}
                loadMoreTriggerRef={loadMoreTriggerRef}
              />
            </div>

            {/* 底部用户面板 - 固定在底部 */}
            <div className="border-t border-[var(--border-color)] min-w-[260px] flex-shrink-0">
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

        <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8">
          <div className="w-full max-w-3xl space-y-8">
            {/* Hero Section */}
            <div className="text-center space-y-3">
              <div className="flex items-center justify-center gap-2 mb-6">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white text-xl">
                  AI
                </div>
              </div>
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--foreground)]">
                方案高参
              </h1>
            </div>

            {/* Input Composer */}
            <div className="relative">
              <form onSubmit={handleSubmit} className="relative rounded-xl border border-gray-200 dark:border-[#3a3a3a] shadow-xl overflow-hidden bg-white dark:bg-[#2a2a2a]">
                {/* 🔥 文件拖拽区域 */}
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleFileDrop}
                  className={`transition-colors ${isDragging ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}
                >
                  <textarea
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    placeholder="描述您的设计需求（必填），可选择性上传辅助文件（支持 PDF、TXT、图片、Word、Excel）..."
                    className="w-full bg-inherit text-gray-900 dark:text-[#e8e8e8] text-base p-5 min-h-[140px] outline-none resize-none placeholder:text-gray-400 dark:placeholder:text-[#8a8a8a]"
                    disabled={isLoading}
                  />
                </div>

                {/* 🔥 已上传文件列表 */}
                {uploadedFiles.length > 0 && (
                  <div className="px-5 pb-3 space-y-2">
                    {uploadedFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-2 p-2 bg-gray-100 dark:bg-gray-800 rounded-lg group"
                      >
                        {getFileIcon(file)}
                        <span className="flex-1 text-sm truncate text-gray-700 dark:text-gray-300">
                          {file.name}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatFileSize(file.size)}
                        </span>
                        {/* 🔥 Phase 3: 预览按钮 */}
                        {(file.type.startsWith('image/') || file.type === 'application/pdf') && (
                          <button
                            type="button"
                            onClick={() => handlePreviewFile(file)}
                            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded transition-opacity"
                            disabled={isLoading}
                            title="预览"
                          >
                            <ImageIcon className="w-4 h-4 text-blue-500" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => removeFile(index)}
                          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-opacity"
                          disabled={isLoading}
                        >
                          <X className="w-4 h-4 text-red-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* 🔥 Phase 3: 上传进度条 */}
                {isLoading && uploadProgress > 0 && uploadProgress < 100 && (
                  <div className="px-5 pb-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        上传中...
                      </span>
                      <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                        {uploadProgress}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between px-5 py-3 border-t border-gray-200 dark:border-[#3a3a3a] rounded-b-xl bg-gray-50 dark:bg-transparent">
                  <div className="flex gap-3 text-[var(--foreground-secondary)]">
                    {/* 🔥 文件上传按钮 */}
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".pdf,.txt,.png,.jpg,.jpeg,.docx,.xlsx"
                      onChange={handleFileSelect}
                      className="hidden"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      disabled={isLoading}
                      title="上传文件（PDF、TXT、图片、Word、Excel）"
                    >
                      <Paperclip className="w-5 h-5" />
                    </button>

                    {/* 🆕 v7.107: 深度思考模式 Toggle */}
                    <label className="flex items-center gap-2 cursor-pointer ml-2">
                      {/* Toggle Switch */}
                      <div className="relative">
                        <input
                          type="checkbox"
                          checked={analysisMode === 'deep_thinking'}
                          onChange={(e) => setAnalysisMode(e.target.checked ? 'deep_thinking' : 'normal')}
                          className="sr-only peer"
                          disabled={isLoading}
                        />
                        <div className={`
                          w-9 h-5 rounded-full transition-all duration-300
                          peer-checked:bg-gray-700 dark:peer-checked:bg-gray-600
                          bg-gray-300 dark:bg-gray-600
                          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                        `}>
                          <div className={`
                            absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-all duration-300
                            peer-checked:translate-x-4
                          `}></div>
                        </div>
                      </div>

                      {/* Text Label */}
                      <span className={`
                        text-xs font-medium transition-colors duration-300 whitespace-nowrap
                        ${analysisMode === 'deep_thinking'
                          ? 'text-gray-700 dark:text-gray-300'
                          : 'text-gray-600 dark:text-gray-400'}
                      `}>
                        深度思考
                      </span>
                    </label>
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading || !userInput.trim()}
                    className={`
                      p-2 rounded-lg transition-all
                      ${userInput.trim()
                        ? 'bg-gray-700 dark:bg-gray-600 text-white hover:bg-gray-600 dark:hover:bg-gray-500 hover:scale-105'
                        : 'bg-transparent text-[#666666] cursor-not-allowed opacity-50'}
                    `}
                    title={userInput.trim() ? '发送' : '请输入文字描述您的需求'}
                  >
                    {isLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-red-900/20 border border-red-900/50 rounded-lg text-red-400 text-sm text-center">
                {error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 🔥 Phase 3: File Preview Modal */}
      {previewFile && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={handleClosePreview}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                {getFileIcon(previewFile)}
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {previewFile.name}
                </span>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  ({formatFileSize(previewFile.size)})
                </span>
              </div>
              <button
                onClick={handleClosePreview}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 overflow-auto max-h-[calc(90vh-80px)]">
              {previewUrl && previewFile.type.startsWith('image/') && (
                <img
                  src={previewUrl}
                  alt={previewFile.name}
                  className="max-w-full h-auto mx-auto rounded-lg"
                />
              )}

              {previewUrl && previewFile.type === 'application/pdf' && (
                <iframe
                  src={previewUrl}
                  className="w-full h-[calc(90vh-120px)] border-0 rounded-lg"
                  title={previewFile.name}
                />
              )}

              {!previewUrl && (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <File className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium mb-2">{previewFile.name}</p>
                  <p className="text-sm">此文件类型不支持预览</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
