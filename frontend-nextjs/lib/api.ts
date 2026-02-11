// lib/api.ts
// 封装所有与 FastAPI 后端的通信

import axios from 'axios';
import type {
  StartAnalysisRequest,
  StartAnalysisResponse,
  AnalysisStatus,
  AnalysisReport,
  ImageGenerationParams,  // 🔥 v7.41
  SuggestedPrompt  // 🔥 v7.41
} from '@/types';

// API 基础 URL（从环境变量读取，开发环境默认 localhost:8000）
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

// 创建 axios 实例,统一配置
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,  // 120 秒超时（LLM 操作通常需要 40-60 秒）
  headers: {
    'Content-Type': 'application/json',
  },
});

// 🔒 添加请求拦截器：自动添加 JWT Token
apiClient.interceptors.request.use(
  (config) => {
    // 从 localStorage 读取 Token
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('wp_jwt_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// API 方法集合
export const api = {
  // 启动分析
  async startAnalysis(data: StartAnalysisRequest): Promise<StartAnalysisResponse> {
    try {
      const response = await apiClient.post<StartAnalysisResponse>('/api/analysis/start', data);
      return response.data;
    } catch (error: any) {
      // 打印详细错误信息
      console.error('Start analysis failed:', error?.message, error?.response?.status, error?.response?.data);
      throw error;
    }
  },

  // 查询状态
  async getStatus(sessionId: string): Promise<AnalysisStatus> {
    const response = await apiClient.get<AnalysisStatus>(`/api/analysis/status/${sessionId}`);
    return response.data;
  },

  // 获取报告
  async getReport(sessionId: string): Promise<AnalysisReport> {
    const response = await apiClient.get<AnalysisReport>(`/api/analysis/report/${sessionId}`);
    return response.data;
  },

  // 恢复工作流（用于交互节点）
  async resumeAnalysis(sessionId: string, resumeValue: string | Record<string, unknown>): Promise<void> {
    await apiClient.post('/api/analysis/resume', {
      session_id: sessionId,
      resume_value: resumeValue,
    });
  },

  // ✅ v7.105.4: 修复分页 - 归档会话offset根据page动态计算
  async getSessions(page: number = 1, pageSize: number = 20, includeArchived: boolean = true): Promise<{
    total: number;
    sessions: Array<{ session_id: string; status: string; mode: string; created_at: string; user_input: string }>;
    has_next: boolean;
  }> {
    try {
      if (!includeArchived) {
        // 仅获取活跃会话（快速）
        const response = await apiClient.get('/api/sessions', {
          params: { page, page_size: pageSize }
        });
        return response.data;
      }

      // 🔥 v7.105.4: 修复策略 - 活跃会话为空时，直接从归档中按页码取数据
      const activeResponse = await apiClient.get('/api/sessions', {
        params: { page, page_size: pageSize }
      });

      const activeSessions = activeResponse.data.sessions || [];
      const activeTotal = activeResponse.data.total || 0;

      // 如果活跃会话已满足一页，直接返回（避免查询归档）
      if (activeSessions.length >= pageSize) {
        return activeResponse.data;
      }

      // 🔥 v7.105.6: 活跃会话不足一页时，从归档补充
      // 关键修复：正确计算归档offset
      const remaining = pageSize - activeSessions.length;

      // 计算归档offset - 把活跃和归档看成一个整体
      // 总数据流：[活跃1-19] [归档1-164]
      // 第1页：取[0-19] → 活跃[0-18] + 归档[0] → offset=0
      // 第2页：取[20-39] → 归档[1-20] → offset=1
      // 第3页：取[40-59] → 归档[21-40] → offset=21
      const startPos = (page - 1) * pageSize;
      const archivedOffset = Math.max(0, startPos - activeTotal);

      // 🔥 v7.105.8: 添加详细日志追踪分页问题
      console.log(`[API] 📖 getSessions | page=${page} | pageSize=${pageSize} | activeTotal=${activeTotal}`);
      console.log(`[API] 📐 计算 | startPos=${startPos} | archivedOffset=${archivedOffset} | remainingNeeded=${remaining}`);

      const archivedResponse = await apiClient.get('/api/sessions/archived', {
        params: {
          limit: remaining,
          offset: archivedOffset
        }
      });

      const archivedSessions = archivedResponse.data.sessions || [];
      const archivedTotal = archivedResponse.data.total || 0;

      console.log(`[API] ✅ 归档响应 | 返回=${archivedSessions.length}条 | total=${archivedTotal}`);

      // 合并会话
      const allSessions = [...activeSessions, ...archivedSessions];

      // 🔥 v7.105.5: 修复has_next判断 - 使用实际加载的数量
      const hasMoreActive = activeResponse.data.has_next || false;
      const totalLoaded = archivedOffset + archivedSessions.length;
      const hasMoreArchived = totalLoaded < archivedTotal;

      console.log(`[API] getSessions page=${page} | offset=${archivedOffset} | loaded=${archivedSessions.length} | total=${archivedTotal} | hasMore=${hasMoreArchived}`);

      return {
        total: activeTotal + archivedTotal,
        sessions: allSessions,
        has_next: hasMoreActive || hasMoreArchived
      };
    } catch (error) {
      console.error('获取会话列表失败:', error);
      // 如果失败，返回空列表
      return {
        total: 0,
        sessions: [],
        has_next: false
      };
    }
  },

  // 更新会话信息（重命名、置顶等）
  async updateSession(sessionId: string, updates: Record<string, any>): Promise<{ success: boolean; message: string }> {
    // 🔧 v7.303: 智能路由 - 优先尝试更新归档会话，失败则尝试活跃会话
    try {
      // 1. 先尝试更新归档会话（大部分历史会话都是归档的）
      const archivedResponse = await apiClient.patch(`/api/sessions/archived/${sessionId}`, updates);
      return archivedResponse.data;
    } catch (archivedError: any) {
      // 2. 如果归档会话不存在（404），尝试更新活跃会话
      if (archivedError?.response?.status === 404) {
        const activeResponse = await apiClient.patch(`/api/sessions/${sessionId}`, updates);
        return activeResponse.data;
      }
      // 3. 其他错误直接抛出
      throw archivedError;
    }
  },

  // 删除会话
  async deleteSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/api/sessions/${sessionId}`);
    return response.data;
  },

  // 🆕 v7.189: 创建搜索会话（自动携带 JWT Token）
  async createSearchSession(query: string, deepMode: boolean = true): Promise<{
    success: boolean;
    session_id?: string;
    query?: string;
    error?: string;
  }> {
    const response = await apiClient.post('/api/search/session/create', {
      query,
      deep_mode: deepMode,
    });
    return response.data;
  },

  // 🆕 v7.189: 删除搜索会话
  async deleteSearchSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/api/search/session/${sessionId}`);
    return response.data;
  },

  // 🔥 新增: 生成智能推荐问题
  async generateFollowupQuestions(sessionId: string): Promise<{ questions: string[]; source?: 'llm' | 'fallback'; message?: string }> {
    const response = await apiClient.post(`/api/analysis/report/${sessionId}/suggest-questions`);
    return response.data;
  },

  // 🔥 v7.108.2 修改: 支持图片上传（multipart/form-data）
  async submitFollowupQuestion(
    sessionId: string,
    question: string,
    image?: File
  ): Promise<{ session_id: string; status: string; message: string }> {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('question', question);
    formData.append('requires_analysis', 'false');  // 启用对话模式而非重新分析

    if (image) {
      formData.append('image', image);
    }

    const response = await apiClient.post(`/api/analysis/followup`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data; // 返回原会话ID，不是新ID
  },

  // 🔥 v3.11 新增: 获取追问历史（支持连续对话）
  async getFollowupHistory(sessionId: string): Promise<{
    session_id: string;
    total_turns: number;
    history: Array<{
      turn_id: number;
      question: string;
      answer: string;
      intent: string;
      referenced_sections: string[];
      timestamp: string;
    }>
  }> {
    const response = await apiClient.get(`/api/analysis/${sessionId}/followup-history`);
    return response.data;
  },

  // 🔥 新增: 支持文件上传的分析接口
  async startAnalysisWithFiles(
    formData: FormData,
    onProgress?: (progress: number) => void
  ): Promise<StartAnalysisResponse> {
    try {
      const response = await axios.post<StartAnalysisResponse>(
        `${API_BASE_URL}/api/analysis/start-with-files`,
        formData,
        {
          timeout: 120000,
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          // 🔥 Phase 3: 上传进度追踪
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total && onProgress) {
              const percentCompleted = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              onProgress(percentCompleted);
            }
          },
        }
      );
      return response.data;
    } catch (error: any) {
      console.error('Start analysis with files failed:', error?.message, error?.response?.status, error?.response?.data);
      throw error;
    }
  },

  // 🔥 v7.41: 概念图像管理 API

  /**
   * 重新生成专家概念图
   * @param sessionId 会话ID
   * @param expertName 专家名称
   * @param params 生成参数
   */
  async regenerateImage(
    sessionId: string,
    expertName: string,
    params: ImageGenerationParams & {
      save_as_copy?: boolean;
      image_id?: string;
    }
  ): Promise<{
    success: boolean;
    image_url?: string;
    image_id?: string;
    error?: string;
  }> {
    const response = await apiClient.post(`/api/analysis/regenerate-image/${sessionId}`, {
      expert_name: expertName,
      new_prompt: params.prompt,
      save_as_copy: params.save_as_copy ?? false,
      image_id: params.image_id,
      aspect_ratio: params.aspect_ratio ?? '16:9',
      style_type: params.style_type
    });
    return response.data;
  },

  /**
   * 为专家新增概念图
   * @param sessionId 会话ID
   * @param expertName 专家名称
   * @param params 生成参数
   */
  async addImage(
    sessionId: string,
    expertName: string,
    params: ImageGenerationParams
  ): Promise<{
    success: boolean;
    image?: {
      id: string;
      image_url: string;
      prompt: string;
    };
    error?: string;
  }> {
    const response = await apiClient.post(`/api/analysis/add-image/${sessionId}`, {
      expert_name: expertName,
      prompt: params.prompt,
      aspect_ratio: params.aspect_ratio ?? '16:9',
      style_type: params.style_type
    });
    return response.data;
  },

  /**
   * 删除专家概念图
   * @param sessionId 会话ID
   * @param expertName 专家名称
   * @param imageId 图像ID（可选，不传则删除所有）
   */
  async deleteImage(
    sessionId: string,
    expertName: string,
    imageId?: string
  ): Promise<{
    success: boolean;
    error?: string;
  }> {
    const response = await apiClient.delete(`/api/analysis/delete-image/${sessionId}`, {
      data: {
        expert_name: expertName,
        image_id: imageId
      }
    });
    return response.data;
  },

  /**
   * 获取专家概念图的推荐提示词
   * @param sessionId 会话ID
   * @param expertName 专家名称
   */
  async suggestImagePrompts(
    sessionId: string,
    expertName: string
  ): Promise<{
    success: boolean;
    suggestions: SuggestedPrompt[];
    extracted_keywords?: string[];
    error?: string;
  }> {
    const response = await apiClient.get(`/api/analysis/suggest-prompts/${sessionId}/${encodeURIComponent(expertName)}`);
    return response.data;
  },

  // 🔥 v7.48: 图片对话历史 API

  /**
   * 获取图片对话历史
   * @param sessionId 会话ID
   * @param expertName 专家名称
   */
  async getImageChatHistory(
    sessionId: string,
    expertName: string
  ): Promise<{
    success: boolean;
    history?: {
      expert_name: string;
      session_id: string;
      turns: Array<{
        turn_id: string;
        type: 'user' | 'assistant';
        timestamp: string;
        prompt?: string;
        aspect_ratio?: string;
        style_type?: string;
        reference_image_url?: string;
        image?: {
          expert_name: string;
          image_url: string;
          prompt: string;
          prompt_used?: string;
          id?: string;
          aspect_ratio?: string;
          style_type?: string;
          created_at?: string;
        };
        error?: string;
      }>;
      created_at: string;
      updated_at: string;
    };
    error?: string;
  }> {
    try {
      const response = await apiClient.get(`/api/analysis/image-chat-history/${sessionId}/${encodeURIComponent(expertName)}`);
      return response.data;
    } catch (error: any) {
      if (error?.response?.status === 404) {
        return { success: false, error: '对话历史不存在' };
      }
      throw error;
    }
  },

  /**
   * 保存图片对话历史
   * @param sessionId 会话ID
   * @param expertName 专家名称
   * @param turns 对话轮次
   */
  async saveImageChatHistory(
    sessionId: string,
    expertName: string,
    turns: Array<{
      turn_id: string;
      type: 'user' | 'assistant';
      timestamp: string;
      prompt?: string;
      aspect_ratio?: string;
      style_type?: string;
      reference_image_url?: string;
      image?: {
        expert_name: string;
        image_url: string;
        prompt: string;
        prompt_used?: string;
        id?: string;
        aspect_ratio?: string;
        style_type?: string;
        created_at?: string;
      };
      error?: string;
    }>
  ): Promise<{
    success: boolean;
    error?: string;
  }> {
    const response = await apiClient.post(`/api/analysis/image-chat-history/${sessionId}/${encodeURIComponent(expertName)}`, {
      turns
    });
    return response.data;
  },

  /**
   * 带上下文的图片生成（支持多轮对话）
   * @param sessionId 会话ID
   * @param expertName 专家名称
   * @param params 生成参数（含上下文）
   */
  async regenerateImageWithContext(
    sessionId: string,
    expertName: string,
    params: {
      prompt: string;
      aspect_ratio?: string;
      style_type?: string;
      reference_image?: string;
      context?: string;  // 多轮对话上下文
      // 🔥 v7.61: Vision 分析参数
      use_vision_analysis?: boolean;
      vision_focus?: 'comprehensive' | 'style' | 'composition' | 'colors';
      // 🔥 v7.62: Inpainting 编辑参数
      mask_image?: string;  // Mask 图像 Base64（黑色=保留，透明=编辑）
      edit_mode?: boolean;  // 是否为编辑模式
    }
  ): Promise<{
    success: boolean;
    image_url?: string;
    image_id?: string;
    image_data?: any;  // 🔥 v7.62: 包含模式信息
    mode?: 'generation' | 'inpainting';  // 🔥 v7.62: 实际使用的模式
    error?: string;
  }> {
    const response = await apiClient.post(`/api/analysis/regenerate-image-with-context/${sessionId}`, {
      expert_name: expertName,
      prompt: params.prompt,
      aspect_ratio: params.aspect_ratio ?? '16:9',
      style_type: params.style_type,
      reference_image: params.reference_image,
      context: params.context,
      // 🔥 v7.61: 添加 Vision 参数
      use_vision_analysis: params.use_vision_analysis,
      vision_focus: params.vision_focus,
      // 🔥 v7.62: 添加 Inpainting 参数
      mask_image: params.mask_image,
      edit_mode: params.edit_mode
    });
    return response.data;
  },

  // 🆕 v7.189: 迁移所有guest会话到用户账户
  async migrateGuestSessions(): Promise<{
    success: boolean;
    migrated_count?: number;
    message?: string;
    error?: string;
  }> {
    try {
      const response = await apiClient.post('/api/search/session/migrate');
      return response.data;
    } catch (error) {
      console.error('迁移guest会话失败:', error);
      return { success: false, error: '迁移会话失败' };
    }
  },

  // 🆕 v7.189: 关联单个guest会话到当前用户
  async associateGuestSession(sessionId: string): Promise<{
    success: boolean;
    session_id?: string;
    message?: string;
    error?: string;
  }> {
    try {
      const response = await apiClient.post('/api/search/session/associate', null, {
        params: { session_id: sessionId }
      });
      return response.data;
    } catch (error) {
      console.error('关联guest会话失败:', error);
      return { success: false, error: '关联会话失败' };
    }
  },

  // 🆕 v7.180: 获取搜索历史列表
  async getSearchSessions(limit: number = 50, offset: number = 0): Promise<{
    success: boolean;
    sessions: Array<{
      session_id: string;
      query: string;
      created_at: string;
      source_count: number;
      image_count: number;
      execution_time: number;
    }>;
    count: number;
  }> {
    try {
      const response = await apiClient.get('/api/search/history', {
        params: { limit, offset }
      });
      return response.data;
    } catch (error) {
      console.error('获取搜索历史失败:', error);
      return { success: false, sessions: [], count: 0 };
    }
  },

  // 🆕 v7.180: 获取统一会话列表（分析+搜索合并）
  async getUnifiedSessions(page: number = 1, pageSize: number = 20): Promise<{
    total: number;
    sessions: Array<{
      session_id: string;
      status: string;
      mode: string;
      created_at: string;
      user_input: string;
      session_type: 'analysis' | 'search';  // 🆕 区分类型
      isTemporary?: boolean;
      analysis_mode?: string;  // 🔥 v7.305: 保留分析模式字段
    }>;
    has_next: boolean;
  }> {
    try {
      // 🔥 v7.305 修复策略（最终版）:
      // 策略演进：
      // v1 问题：搜索会话过多（20条）淹没分析会话
      // v2 修复：仅分析会话不足时补充搜索 → 用户反馈：看不到搜索会话
      // v3 最终：按比例混合显示（分析会话优先，但搜索会话也可见）

      // 策略：分析会话获取pageSize，搜索会话获取pageSize/2
      // 合并后按时间排序，取前pageSize条
      // 这样既保证分析会话优先级，又能看到搜索历史

      const analysisData = await this.getSessions(page, pageSize, true);

      // 为分析会话添加类型标记（保留 analysis_mode 字段）
      const analysisSessions = (analysisData.sessions || []).map(s => ({
        ...s,
        session_type: 'analysis' as const
      }));

      // 🎯 关键修复: 始终获取一定数量的搜索会话（约pageSize的50%）
      // 这样可以在时间排序后混合显示
      const searchLimit = Math.ceil(pageSize / 2);  // 10条搜索会话
      const searchOffset = (page - 1) * searchLimit;

      const searchData = await this.getSearchSessions(searchLimit, searchOffset);

      // 转换搜索会话为统一格式
      const searchSessions = (searchData.sessions || []).map(s => ({
        session_id: s.session_id,
        status: 'completed' as const,
        mode: 'search',
        created_at: s.created_at,
        user_input: s.query,
        session_type: 'search' as const
      }));

      // 合并并按时间排序
      const allSessions = [...analysisSessions, ...searchSessions].sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      // 取前pageSize条（按时间自然混合）
      const paginatedSessions = allSessions.slice(0, pageSize);

      return {
        total: analysisData.total + searchData.count,
        sessions: paginatedSessions,
        has_next: analysisData.has_next || searchData.count >= searchLimit
      };
    } catch (error) {
      console.error('获取统一会话列表失败:', error);
      return { total: 0, sessions: [], has_next: false };
    }
  },
};
