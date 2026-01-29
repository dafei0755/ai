// app/page.tsx
// 首页：用户输入需求并启动分析

'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
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
  Paperclip,
  File,
  FileText,
  Image as ImageIcon,
  Sparkles
} from 'lucide-react';
import { api } from '@/lib/api';
import { useWorkflowStore } from '@/store/useWorkflowStore';
import { formatFileSize } from '@/lib/formatters';
import { UserPanel } from '@/components/layout/UserPanel';
import { useAuth } from '@/contexts/AuthContext';
import { useSession } from '@/contexts/SessionContext';
import { SessionSidebar } from '@/components/SessionSidebar';
import { FileTagEditor } from '@/components/FileTagEditor';
import type { UploadedFileMetadata, ImageCategory, DocumentCategory } from '@/types';
// 🔥 v7.109: 进度直接在时间戳后显示，移除了 ProgressBadge 组件
// 🔥 v7.110: 提取侧边栏为公共组件 SessionSidebar
// 🆕 v7.157: 集成文件标签编辑器
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

  // 🔥 v7.180: 分析模式状态 - 搜索/普通思考/深度思考（默认搜索）
  const [analysisMode, setAnalysisMode] = useState<'normal' | 'search' | 'deep_thinking'>('search');

  // 🔥 检测是否在 iframe 中（用于显示主网站链接）
  const isInIframe = typeof window !== 'undefined' && window.self !== window.top;

  // 🆕 v7.157: 文件上传相关状态（带标签元数据）
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileMetadata[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 🔥 Phase 3: 上传进度和预览
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // 🔥 v7.283: 移除本地会话状态管理，使用全局 SessionContext

  // 🔥 v7.9.3: 日期分组函数 - 按相对时间分组会话
  const groupSessionsByDate = useCallback(
    (sessions: Array<{ session_id: string; status: string; created_at: string; user_input: string; isTemporary?: boolean; session_type?: 'analysis' | 'search' }>) => {
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

  // 🆕 v7.157: 添加文件（带验证和元数据初始化）
  const addFiles = (newFiles: File[]) => {
    const validTypes = [
      'application/pdf',
      'text/plain',
      'image/png',
      'image/jpeg',
      'image/jpg',
      'image/webp',  // 🆕 v7.159: 支持webp格式
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'       // .xlsx
    ];

    const imageTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

    const validFileMetadata: UploadedFileMetadata[] = newFiles
      .filter(file => {
        // 验证文件类型
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
      })
      .map(file => {
        const isImage = imageTypes.includes(file.type);
        return {
          file,
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          categories: [] as ImageCategory[] | DocumentCategory[],
          customDescription: '',
          previewUrl: isImage ? URL.createObjectURL(file) : undefined,
          isImage
        };
      });

    setUploadedFiles(prev => [...prev, ...validFileMetadata]);
  };

  // 🆕 v7.157: 更新文件元数据
  const updateFileMetadata = (id: string, updated: UploadedFileMetadata) => {
    setUploadedFiles(prev =>
      prev.map(f => f.id === id ? updated : f)
    );
  };

  // 🆕 v7.157: 移除文件（清理预览URL）
  const removeFile = (id: string) => {
    setUploadedFiles(prev => {
      const file = prev.find(f => f.id === id);
      if (file?.previewUrl) {
        URL.revokeObjectURL(file.previewUrl);
      }
      return prev.filter(f => f.id !== id);
    });
  };

  // 清理所有预览URL
  useEffect(() => {
    return () => {
      uploadedFiles.forEach(f => {
        if (f.previewUrl) {
          URL.revokeObjectURL(f.previewUrl);
        }
      });
    };
  }, []);

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

    // 🆕 v7.180: 搜索模式 - 在主页创建会话后跳转到结果页（只保留深度搜索）
    if (analysisMode === 'search') {
      const trimmedInput = userInput.trim();
      if (!trimmedInput) {
        setError('请输入搜索内容');
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // 🆕 v7.189: 使用 apiClient 自动携带 JWT Token，避免创建 guest- 会话
        const data = await api.createSearchSession(trimmedInput, true);

        if (data.success && data.session_id) {
          // 🆕 v7.180: 添加到本地会话列表（乐观更新）
          const newSession = {
            session_id: data.session_id,
            status: 'pending',
            created_at: new Date().toISOString(),
            user_input: trimmedInput,
            session_type: 'search' as const
          };
          setSessions(prev => [newSession, ...prev]);

          // 🆕 v7.290: 记录会话创建时间到 localStorage，用于区分新旧会话
          const recentSessionsJson = localStorage.getItem('recent_search_sessions');
          const recentSessions: Record<string, number> = recentSessionsJson ? JSON.parse(recentSessionsJson) : {};
          recentSessions[data.session_id] = Date.now();
          localStorage.setItem('recent_search_sessions', JSON.stringify(recentSessions));

          setUserInput('');
          router.push(`/search/${data.session_id}`);
        } else {
          setError('创建搜索会话失败，请重试');
        }
      } catch (error) {
        console.error('创建搜索会话失败:', error);
        setError('网络错误，请重试');
      } finally {
        setIsLoading(false);
      }
      return;
    }

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

      // 🆕 v7.157: 根据是否有文件选择不同的API
      if (uploadedFiles.length > 0) {
        // 使用 FormData 上传文件
        const formData = new FormData();
        formData.append('user_input', userInput.trim());
        formData.append('user_id', 'web_user');
        formData.append('analysis_mode', analysisMode);  // 🆕 v7.107

        // 🆕 v7.157: 添加文件和元数据
        const fileMetadataList = uploadedFiles.map(fm => ({
          filename: fm.file.name,
          categories: fm.categories,
          custom_description: fm.customDescription,
          is_image: fm.isImage
        }));
        formData.append('file_metadata', JSON.stringify(fileMetadataList));

        uploadedFiles.forEach(fm => {
          formData.append('files', fm.file);
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

      // 🆕 v7.290: 记录新创建的分析会话到 localStorage（用于检测旧会话）
      const recentSessionsJson = localStorage.getItem('recent_analysis_sessions');
      const recentSessions: Record<string, number> = recentSessionsJson ? JSON.parse(recentSessionsJson) : {};
      recentSessions[response.session_id] = Date.now();
      // 保留最近100个会话记录，防止localStorage过大
      const sessionIds = Object.keys(recentSessions);
      if (sessionIds.length > 100) {
        // 删除最旧的会话记录
        const sortedIds = sessionIds.sort((a, b) => recentSessions[a] - recentSessions[b]);
        sortedIds.slice(0, sessionIds.length - 100).forEach(id => delete recentSessions[id]);
      }
      localStorage.setItem('recent_analysis_sessions', JSON.stringify(recentSessions));
      console.log('📝 记录新会话到 localStorage:', response.session_id);

      // 🆕 v7.290: 同时保存用户输入到 localStorage（用于错误页面显示）
      const userInputsJson = localStorage.getItem('analysis_user_inputs');
      const userInputs: Record<string, string> = userInputsJson ? JSON.parse(userInputsJson) : {};
      userInputs[response.session_id] = displayText;
      // 同样保留最近100条
      const inputIds = Object.keys(userInputs);
      if (inputIds.length > 100) {
        const sortedInputIds = Object.keys(userInputs).sort((a, b) => {
          const aTime = recentSessions[a] || 0;
          const bTime = recentSessions[b] || 0;
          return aTime - bTime;
        });
        sortedInputIds.slice(0, inputIds.length - 100).forEach(id => delete userInputs[id]);
      }
      localStorage.setItem('analysis_user_inputs', JSON.stringify(userInputs));
      console.log('📝 保存用户输入到 localStorage:', response.session_id);

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

  // 🔥 v7.283: 移除本地会话操作函数，使用全局 SessionContext

  // 🎯 v7.158: 未登录时直接跳转 WordPress SSO 登录页
  // 完全禁止未登录访问，自动重定向到登录页
  // 🔧 [临时修改] 注释掉强制登录逻辑，允许本地测试
  /*
  if (!authLoading && !user) {
    // 🔥 v7.158: 直接跳转到 WordPress SSO 登录页
    // 登录成功后会自动返回当前页面
    if (typeof window !== 'undefined') {
      const currentUrl = window.location.href;
      const loginUrl = `https://www.ucppt.com/login?redirect_to=${encodeURIComponent(currentUrl)}`;
      console.log('[HomePage v7.158] 🔒 未登录，跳转到 WordPress SSO 登录页:', loginUrl);
      window.location.href = loginUrl;
    }

    // 跳转过程中显示加载状态
    return (
      <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-gray-500" />
          <p className="text-[var(--foreground-secondary)]">正在跳转到登录页...</p>
        </div>
      </div>
    );
  }
  */

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

        <div
          className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8"
          onMouseDown={(e) => {
            // 🆕 v7.242: 阻止点击空白区域时触发 textarea 焦点
            if (e.target === e.currentTarget) {
              e.preventDefault();
            }
          }}
        >
          <div
            className="w-full max-w-3xl space-y-8"
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
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
                  <Sparkles size={20} />
                </div>
                <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[var(--foreground)]">
                  方案高参
                </h1>
              </div>
            </div>

            {/* Input Composer */}
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
                    placeholder={
                      analysisMode === 'search'
                        ? "输入您想了解的问题，联网搜索最新资料..."
                        : analysisMode === 'deep_thinking'
                          ? "描述您的设计需求，生成专家概念图，适合复杂设计项目..."
                          : "描述您的设计需求（必填），快速分析，适合简单需求..."
                    }
                    className="w-full bg-inherit text-gray-900 dark:text-[#e8e8e8] text-base leading-6 px-6 pt-6 pb-6 min-h-[170px] outline-none resize-none placeholder:text-gray-400 dark:placeholder:text-[#8a8a8a]"
                    disabled={isLoading}
                  />
                </div>

                {/* 🆕 v7.157: 已上传文件列表（带标签编辑器） */}
                {uploadedFiles.length > 0 && (
                  <div className="px-5 pb-3 space-y-3 max-h-[400px] overflow-y-auto">
                    {uploadedFiles.map((fileMetadata) => (
                      <FileTagEditor
                        key={fileMetadata.id}
                        fileMetadata={fileMetadata}
                        onUpdate={(updated) => updateFileMetadata(fileMetadata.id, updated)}
                        onRemove={() => removeFile(fileMetadata.id)}
                        disabled={isLoading}
                      />
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

                <div className="flex items-center justify-between pl-3 pr-5 py-3 border-t border-gray-200 dark:border-[#3a3a3a] rounded-b-xl bg-gray-50 dark:bg-transparent">
                  <div className="flex gap-2 text-[var(--foreground-secondary)]">
                    {/* 🔥 文件上传按钮 - 🆕 v7.242: 搜索模式下保留占位空间，保持按钮位置一致 */}
                    <div className="w-9 h-9 flex-shrink-0">
                      {analysisMode !== 'search' && (
                        <>
                          <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,.docx,.xlsx"
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
                        </>
                      )}
                    </div>

                    {/* 🆕 v7.180: 分析模式选择器 - 搜索/普通思考/深度思考（搜索优先） */}
                    <div className="flex items-center gap-1">
                      {/* 分段按钮组 */}
                      <div className={`
                        flex items-center gap-1 rounded-full p-1 transition-all duration-300
                        bg-gray-200 dark:bg-gray-700
                        ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                      `}>
                        {/* 搜索模式 - 🆕 v7.180: 默认模式，白色样式 */}
                        <button
                          type="button"
                          onClick={() => !isLoading && setAnalysisMode('search')}
                          disabled={isLoading}
                          className={`
                            px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-300 whitespace-nowrap
                            ${analysisMode === 'search'
                              ? 'bg-white dark:bg-gray-600 text-gray-800 dark:text-white shadow-sm'
                              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}
                          `}
                        >
                          搜索
                        </button>

                        {/* 普通思考 - 蓝色样式 */}
                        <button
                          type="button"
                          onClick={() => !isLoading && setAnalysisMode('normal')}
                          disabled={isLoading}
                          className={`
                            px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-300 whitespace-nowrap
                            ${analysisMode === 'normal'
                              ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-sm'
                              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}
                          `}
                        >
                          普通思考
                        </button>

                        {/* 深度思考 - 橙色样式 */}
                        <button
                          type="button"
                          onClick={() => !isLoading && setAnalysisMode('deep_thinking')}
                          disabled={isLoading}
                          className={`
                            px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-300 whitespace-nowrap
                            ${analysisMode === 'deep_thinking'
                              ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm'
                              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}
                          `}
                        >
                          深度思考
                        </button>
                      </div>
                    </div>
                  </div>
                  {/* 🆕 v7.158: 发送按钮 - DeepSeek 风格 */}
                  <button
                    type="submit"
                    disabled={isLoading || !userInput.trim()}
                    className={`
                      p-2.5 rounded-full transition-all duration-300
                      ${userInput.trim()
                        ? 'bg-blue-500 text-white hover:bg-blue-600 hover:scale-105 shadow-lg'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'}
                    `}
                    title={userInput.trim() ? '发送' : '请输入文字描述您的需求'}
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
