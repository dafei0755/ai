// store/useWorkflowStore.ts
// Zustand 状态管理：存储工作流相关的全局状态

import { create } from 'zustand';
import type { AnalysisStatus } from '@/types';

interface WorkflowState {
  // 当前会话 ID
  sessionId: string | null;
  setSessionId: (id: string | null) => void;

  // 会话状态
  status: AnalysisStatus | null;
  setStatus: (status: AnalysisStatus | null) => void;

  // 加载状态
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;

  // 错误信息
  error: string | null;
  setError: (error: string | null) => void;

  // 重置所有状态
  reset: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

  status: null,
  setStatus: (status) => set({ status }),

  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  error: null,
  setError: (error) => set({ error }),

  reset: () => set({
    sessionId: null,
    status: null,
    isLoading: false,
    error: null,
  }),
}));
