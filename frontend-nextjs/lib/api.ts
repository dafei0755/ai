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

  // 获取所有会话列表（包括活跃和归档的会话）
  async getSessions(): Promise<{ total: number; sessions: Array<{ session_id: string; status: string; mode: string; created_at: string; user_input: string }> }> {
    try {
      // 同时获取活跃会话和归档会话
      const [activeResponse, archivedResponse] = await Promise.all([
        apiClient.get('/api/sessions'),
        apiClient.get('/api/sessions/archived')
      ]);

      // 合并两个列表
      const allSessions = [
        ...activeResponse.data.sessions,
        ...archivedResponse.data.sessions
      ];

      // 按创建时间倒序排序（最新的在前面）
      allSessions.sort((a, b) => {
        const timeA = new Date(a.created_at).getTime();
        const timeB = new Date(b.created_at).getTime();
        return timeB - timeA;
      });

      return {
        total: allSessions.length,
        sessions: allSessions
      };
    } catch (error) {
      console.error('获取会话列表失败:', error);
      // 如果失败，至少返回活跃会话
      const response = await apiClient.get('/api/sessions');
      return response.data;
    }
  },

  // 更新会话信息（重命名、置顶等）
  async updateSession(sessionId: string, updates: Record<string, any>): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.patch(`/api/sessions/${sessionId}`, updates);
    return response.data;
  },

  // 删除会话
  async deleteSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/api/sessions/${sessionId}`);
    return response.data;
  },

  // 🔥 新增: 生成智能推荐问题
  async generateFollowupQuestions(sessionId: string): Promise<{ questions: string[]; source?: 'llm' | 'fallback'; message?: string }> {
    const response = await apiClient.post(`/api/analysis/report/${sessionId}/suggest-questions`);
    return response.data;
  },

  // 🔥 v3.11 修改: 提交追问（在原会话上追加，不创建新会话）
  async submitFollowupQuestion(sessionId: string, question: string): Promise<{ session_id: string; status: string; message: string }> {
    const response = await apiClient.post(`/api/analysis/followup`, {
      session_id: sessionId,
      question: question,
      requires_analysis: false // 启用对话模式而非重新分析
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
};
