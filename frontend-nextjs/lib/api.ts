// lib/api.ts
// 封装所有与 FastAPI 后端的通信

import axios from 'axios';
import type { 
  StartAnalysisRequest, 
  StartAnalysisResponse, 
  AnalysisStatus, 
  AnalysisReport 
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
};
