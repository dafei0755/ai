// app/page.tsx
// 首页：用户输入需求并启动分析

'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Send,
  Plus,
  MessageSquare,
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
// 🔥 v7.107: 导入新组件
import { DeepThinkingBadge } from '@/components/DeepThinkingBadge';
import { ProgressBadge } from '@/components/ProgressBadge';

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
        } else if (sessionDay.getTime() >= last30Days.getTime()) {
          groups.last30Days.push(session);
        } else {
          // 按月份分组（格式：YYYY-MM）
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

  // 加载历史会话列表（仅在已登录时）
  useEffect(() => {
    // 🔒 安全检查：只有已登录用户才能获取会话列表
    if (!user) {
      console.log('[HomePage] 用户未登录，清空会话列表');
      setSessions([]);
      return;
    }

    const fetchSessions = async () => {
      try {
        const data = await api.getSessions();
        setSessions(dedupeSessions(data.sessions || []));
      } catch (err) {
        console.error('获取会话列表失败:', err);
      }
    };

    fetchSessions();
  }, [dedupeSessions, user]); // 🔒 依赖user，登录状态变化时重新获取

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
        // 从本地会话列表中移除
        setSessions(prevSessions => prevSessions.filter(s => s.session_id !== sessionId));
        alert('删除成功');
      } catch (err) {
        console.error('删除失败:', err);
        alert('删除失败，请重试');
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
            <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center text-white text-2xl">
              AI
            </div>
          </div>
          <h1 className="text-2xl font-semibold text-[var(--foreground)]">
            极致概念 设计高参
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
              className="w-full px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium rounded-lg transition-all"
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
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500" />
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

      {/* Sidebar */}
      <div 
        className={`${
          isSidebarOpen ? 'w-[260px] translate-x-0' : 'w-0 -translate-x-full md:translate-x-0 md:w-0'
        } bg-[var(--sidebar-bg)] border-r border-[var(--border-color)] transition-all duration-300 ease-in-out flex flex-col fixed md:relative h-full z-40 overflow-hidden`}
      >
        <div className="p-4 flex items-center justify-between min-w-[260px]">
          <div className="flex items-center gap-2 font-semibold text-lg text-[var(--foreground)]">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
              AI
            </div>
            <span>设计高参</span>
          </div>
          {/* Mobile Close Button */}
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="md:hidden p-1 text-[var(--foreground-secondary)] hover:text-[var(--foreground)]"
          >
            <X size={20} />
          </button>
        </div>

        <div className="px-3 py-2 min-w-[260px]">
          <button 
            onClick={() => window.location.reload()}
            className="w-full flex items-center gap-2 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white px-4 py-2.5 rounded-lg transition-colors shadow-sm"
          >
            <Plus size={18} />
            <span className="whitespace-nowrap">开启新对话</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 min-w-[260px]">
          {/* 🔥 v7.9.3: 按日期分组显示会话 */}
          {uniqueSessions.length === 0 ? (
            <div className="text-xs text-gray-500 px-3 py-2 text-center">暂无历史记录</div>
          ) : (
            <>
              {/* 今天 */}
              {groupedSessions.today.length > 0 && (
                <div className="mb-4">
                  <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">今天</div>
                  {groupedSessions.today.map((session: any) => (
                    <div key={`homepage-${session.session_id}`} className="relative group">
                      <button
                        onClick={() => !session.isTemporary && router.push(`/analysis/${session.session_id}`)}
                        className={`w-full text-sm text-[var(--foreground-secondary)] hover:bg-[var(--card-bg)] hover:text-[var(--foreground)] px-3 py-2 rounded-lg transition-colors text-left ${session.isTemporary ? 'opacity-60 cursor-wait' : ''}`}
                        disabled={session.isTemporary}
                      >
                        <div className="flex items-center gap-2">
                          {session.isTemporary && (
                            <Loader2 size={14} className="animate-spin text-blue-500 flex-shrink-0" />
                          )}
                          <div className="flex-1 pr-6 line-clamp-2">{session.user_input || '未命名会话'}</div>
                        </div>
                        
                        {/* 🔥 v7.107: 显示徽章 */}
                        <div className="flex items-center gap-1.5 mt-1">
                          <div className="text-xs text-gray-500">
                            {session.isTemporary ? '正在创建...' : new Date(session.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </div>
                          {!session.isTemporary && session.analysis_mode === 'deep_thinking' && (
                            <DeepThinkingBadge />
                          )}
                          {!session.isTemporary && session.status === 'running' && session.progress !== undefined && (
                            <ProgressBadge progress={session.progress} currentStage={session.current_stage} />
                          )}
                        </div>
                      </button>

                      {/* 菜单按钮 - 临时记录不显示 */}
                      {!session.isTemporary && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenSessionId(menuOpenSessionId === session.session_id ? null : session.session_id);
                          }}
                          className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-[var(--sidebar-bg)] rounded transition-opacity"
                        >
                          <MoreVertical size={16} />
                        </button>
                      )}

                      {/* 下拉菜单 */}
                      {menuOpenSessionId === session.session_id && (
                        <>
                          {/* 点击遮罩关闭菜单 */}
                          <div
                            className="fixed inset-0 z-10"
                            onClick={() => setMenuOpenSessionId(null)}
                          />
                          <div className="absolute right-0 top-8 z-20 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg py-1 min-w-[140px]">
                            <button
                              onClick={() => handleRenameSession(session.session_id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left"
                            >
                              <Edit2 size={14} />
                              <span>重命名</span>
                            </button>
                            <button
                              onClick={() => handlePinSession(session.session_id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left"
                            >
                              <Pin size={14} />
                              <span>置顶</span>
                            </button>
                            <button
                              onClick={() => handleShareSession(session.session_id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left"
                            >
                              <Share2 size={14} />
                              <span>分享</span>
                            </button>
                            <div className="border-t border-[var(--border-color)] my-1"></div>
                            <button
                              onClick={() => handleDeleteSession(session.session_id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-900/20 text-red-400 transition-colors text-left"
                            >
                              <Trash2 size={14} />
                              <span>删除</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 昨天 */}
              {groupedSessions.yesterday.length > 0 && (
                <div className="mb-4">
                  <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">昨天</div>
                  {groupedSessions.yesterday.map((session: any) => (
                    <div key={`homepage-${session.session_id}`} className="relative group">
                      <button
                        onClick={() => !session.isTemporary && router.push(`/analysis/${session.session_id}`)}
                        className={`w-full text-sm text-[var(--foreground-secondary)] hover:bg-[var(--card-bg)] hover:text-[var(--foreground)] px-3 py-2 rounded-lg transition-colors text-left ${session.isTemporary ? 'opacity-60 cursor-wait' : ''}`}
                        disabled={session.isTemporary}
                      >
                        <div className="flex items-center gap-2">
                          {session.isTemporary && (
                            <Loader2 size={14} className="animate-spin text-blue-500 flex-shrink-0" />
                          )}
                          <div className="flex-1 pr-6 line-clamp-2">{session.user_input || '未命名会话'}</div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {session.isTemporary ? '正在创建...' : new Date(session.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </button>

                      {!session.isTemporary && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenSessionId(menuOpenSessionId === session.session_id ? null : session.session_id);
                          }}
                          className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-[var(--sidebar-bg)] rounded transition-opacity"
                        >
                          <MoreVertical size={16} />
                        </button>
                      )}

                      {menuOpenSessionId === session.session_id && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setMenuOpenSessionId(null)} />
                          <div className="absolute right-0 top-8 z-20 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg py-1 min-w-[140px]">
                            <button onClick={() => handleRenameSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Edit2 size={14} /><span>重命名</span>
                            </button>
                            <button onClick={() => handlePinSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Pin size={14} /><span>置顶</span>
                            </button>
                            <button onClick={() => handleShareSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Share2 size={14} /><span>分享</span>
                            </button>
                            <div className="border-t border-[var(--border-color)] my-1"></div>
                            <button onClick={() => handleDeleteSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-900/20 text-red-400 transition-colors text-left">
                              <Trash2 size={14} /><span>删除</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 7天内 */}
              {groupedSessions.last7Days.length > 0 && (
                <div className="mb-4">
                  <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">7天内</div>
                  {groupedSessions.last7Days.map((session: any) => (
                    <div key={`homepage-${session.session_id}`} className="relative group">
                      <button
                        onClick={() => !session.isTemporary && router.push(`/analysis/${session.session_id}`)}
                        className={`w-full text-sm text-[var(--foreground-secondary)] hover:bg-[var(--card-bg)] hover:text-[var(--foreground)] px-3 py-2 rounded-lg transition-colors text-left ${session.isTemporary ? 'opacity-60 cursor-wait' : ''}`}
                        disabled={session.isTemporary}
                      >
                        <div className="flex items-center gap-2">
                          {session.isTemporary && (
                            <Loader2 size={14} className="animate-spin text-blue-500 flex-shrink-0" />
                          )}
                          <div className="flex-1 pr-6 line-clamp-2">{session.user_input || '未命名会话'}</div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {session.isTemporary ? '正在创建...' : new Date(session.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </button>

                      {!session.isTemporary && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenSessionId(menuOpenSessionId === session.session_id ? null : session.session_id);
                          }}
                          className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-[var(--sidebar-bg)] rounded transition-opacity"
                        >
                          <MoreVertical size={16} />
                        </button>
                      )}

                      {menuOpenSessionId === session.session_id && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setMenuOpenSessionId(null)} />
                          <div className="absolute right-0 top-8 z-20 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg py-1 min-w-[140px]">
                            <button onClick={() => handleRenameSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Edit2 size={14} /><span>重命名</span>
                            </button>
                            <button onClick={() => handlePinSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Pin size={14} /><span>置顶</span>
                            </button>
                            <button onClick={() => handleShareSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Share2 size={14} /><span>分享</span>
                            </button>
                            <div className="border-t border-[var(--border-color)] my-1"></div>
                            <button onClick={() => handleDeleteSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-900/20 text-red-400 transition-colors text-left">
                              <Trash2 size={14} /><span>删除</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 30天内 */}
              {groupedSessions.last30Days.length > 0 && (
                <div className="mb-4">
                  <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">30天内</div>
                  {groupedSessions.last30Days.map((session: any) => (
                    <div key={`homepage-${session.session_id}`} className="relative group">
                      <button
                        onClick={() => !session.isTemporary && router.push(`/analysis/${session.session_id}`)}
                        className={`w-full text-sm text-[var(--foreground-secondary)] hover:bg-[var(--card-bg)] hover:text-[var(--foreground)] px-3 py-2 rounded-lg transition-colors text-left ${session.isTemporary ? 'opacity-60 cursor-wait' : ''}`}
                        disabled={session.isTemporary}
                      >
                        <div className="flex items-center gap-2">
                          {session.isTemporary && (
                            <Loader2 size={14} className="animate-spin text-blue-500 flex-shrink-0" />
                          )}
                          <div className="flex-1 pr-6 line-clamp-2">{session.user_input || '未命名会话'}</div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {session.isTemporary ? '正在创建...' : new Date(session.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </button>

                      {!session.isTemporary && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenSessionId(menuOpenSessionId === session.session_id ? null : session.session_id);
                          }}
                          className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-[var(--sidebar-bg)] rounded transition-opacity"
                        >
                          <MoreVertical size={16} />
                        </button>
                      )}

                      {menuOpenSessionId === session.session_id && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setMenuOpenSessionId(null)} />
                          <div className="absolute right-0 top-8 z-20 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg py-1 min-w-[140px]">
                            <button onClick={() => handleRenameSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Edit2 size={14} /><span>重命名</span>
                            </button>
                            <button onClick={() => handlePinSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Pin size={14} /><span>置顶</span>
                            </button>
                            <button onClick={() => handleShareSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Share2 size={14} /><span>分享</span>
                            </button>
                            <div className="border-t border-[var(--border-color)] my-1"></div>
                            <button onClick={() => handleDeleteSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-900/20 text-red-400 transition-colors text-left">
                              <Trash2 size={14} /><span>删除</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 按月份分组 */}
              {Object.keys(groupedSessions.byMonth).sort().reverse().map(monthKey => (
                <div key={monthKey} className="mb-4">
                  <div className="text-xs font-medium text-[var(--foreground-secondary)] px-3 py-1 mb-1">{monthKey}</div>
                  {groupedSessions.byMonth[monthKey].map((session: any) => (
                    <div key={`homepage-${session.session_id}`} className="relative group">
                      <button
                        onClick={() => !session.isTemporary && router.push(`/analysis/${session.session_id}`)}
                        className={`w-full text-sm text-[var(--foreground-secondary)] hover:bg-[var(--card-bg)] hover:text-[var(--foreground)] px-3 py-2 rounded-lg transition-colors text-left ${session.isTemporary ? 'opacity-60 cursor-wait' : ''}`}
                        disabled={session.isTemporary}
                      >
                        <div className="flex items-center gap-2">
                          {session.isTemporary && (
                            <Loader2 size={14} className="animate-spin text-blue-500 flex-shrink-0" />
                          )}
                          <div className="flex-1 pr-6 line-clamp-2">{session.user_input || '未命名会话'}</div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {session.isTemporary ? '正在创建...' : new Date(session.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </button>

                      {!session.isTemporary && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenSessionId(menuOpenSessionId === session.session_id ? null : session.session_id);
                          }}
                          className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-[var(--sidebar-bg)] rounded transition-opacity"
                        >
                          <MoreVertical size={16} />
                        </button>
                      )}

                      {menuOpenSessionId === session.session_id && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setMenuOpenSessionId(null)} />
                          <div className="absolute right-0 top-8 z-20 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg py-1 min-w-[140px]">
                            <button onClick={() => handleRenameSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Edit2 size={14} /><span>重命名</span>
                            </button>
                            <button onClick={() => handlePinSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Pin size={14} /><span>置顶</span>
                            </button>
                            <button onClick={() => handleShareSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--sidebar-bg)] transition-colors text-left">
                              <Share2 size={14} /><span>分享</span>
                            </button>
                            <div className="border-t border-[var(--border-color)] my-1"></div>
                            <button onClick={() => handleDeleteSession(session.session_id)} className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-900/20 text-red-400 transition-colors text-left">
                              <Trash2 size={14} /><span>删除</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </>
          )}
        </div>

        {/* 底部区域 */}
        <div className="border-t border-[var(--border-color)] min-w-[260px]">
          {/* 用户面板 */}
          <div className="p-3">
            <UserPanel />
          </div>

        </div>
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
              <span>返回设计知外</span>
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
                极致概念 设计高参
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
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading || !userInput.trim()}
                    className={`
                      p-2 rounded-lg transition-all
                      ${userInput.trim()
                        ? 'bg-[#5b7cf5] text-white hover:bg-[#4d6bfe] hover:scale-105'
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

            {/* 🆕 v7.107: 深度思考模式切换按钮（位于对话框下方） */}
            <div className="flex items-center justify-center mt-3">
              <button
                type="button"
                onClick={() => setAnalysisMode(analysisMode === 'normal' ? 'deep_thinking' : 'normal')}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-all duration-200
                  ${analysisMode === 'deep_thinking'
                    ? 'bg-purple-500/20 border-purple-500 text-purple-400'
                    : 'bg-transparent border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-purple-400 hover:text-purple-400'
                  }
                `}
                disabled={isLoading}
              >
                <div className={`
                  w-5 h-5 rounded border-2 flex items-center justify-center transition-all
                  ${analysisMode === 'deep_thinking'
                    ? 'bg-purple-500 border-purple-500'
                    : 'border-gray-400 dark:border-gray-500'
                  }
                `}>
                  {analysisMode === 'deep_thinking' && (
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <span className="text-sm font-medium">
                  深度思考模式
                </span>
                <span className="text-xs opacity-75">
                  {analysisMode === 'deep_thinking' ? '(3张概念图/交付物)' : '(1张概念图/交付物)'}
                </span>
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-red-900/20 border border-red-900/50 rounded-lg text-red-400 text-sm text-center">
                {error}
              </div>
            )}
          </div>
        </div>
        
        <div className="p-4 text-center text-xs text-[var(--foreground-secondary)]">
          ucppt.com
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
