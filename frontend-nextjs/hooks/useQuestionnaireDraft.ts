/**
 * 🆕 P3优化: 问卷草稿自动保存Hook
 *
 * 在问卷填写过程中自动保存到localStorage，防止数据丢失
 */

import { useEffect, useCallback, useRef } from 'react';

interface QuestionAnswer {
  question_id: string;
  answer: string;
  answered_at?: string;
}

interface DraftData {
  sessionId: string;
  answers: QuestionAnswer[];
  lastSaved: string;
  version: string;
}

const DRAFT_KEY_PREFIX = 'questionnaire_draft_';
const DRAFT_VERSION = '1.0';
const AUTO_SAVE_DELAY = 2000; // 2秒防抖

/**
 * 简单的防抖函数实现
 */
function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): T & { cancel: () => void } {
  let timeoutId: NodeJS.Timeout | null = null;

  const debounced = function (this: any, ...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      func.apply(this, args);
    }, delay);
  } as T & { cancel: () => void };

  debounced.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };

  return debounced;
}

/**
 * 🆕 P3优化: useQuestionnaireDraft Hook
 *
 * @param sessionId - 会话ID
 * @param answers - 当前答案数组
 * @param enabled - 是否启用自动保存
 */
export function useQuestionnaireDraft(
  sessionId: string,
  answers: QuestionAnswer[],
  enabled: boolean = true
) {
  const draftKey = `${DRAFT_KEY_PREFIX}${sessionId}`;
  const isInitialMount = useRef(true);

  /**
   * 保存草稿到localStorage
   */
  const saveDraft = useCallback(() => {
    if (!enabled || !sessionId) return;

    try {
      const draftData: DraftData = {
        sessionId,
        answers,
        lastSaved: new Date().toISOString(),
        version: DRAFT_VERSION
      };

      localStorage.setItem(draftKey, JSON.stringify(draftData));
      console.log('✅ 问卷草稿已自动保存');
    } catch (error) {
      console.error('❌ 保存草稿失败:', error);
    }
  }, [sessionId, answers, enabled, draftKey]);

  /**
   * 防抖保存
   */
  const debouncedSave = useCallback(
    debounce(saveDraft, AUTO_SAVE_DELAY),
    [saveDraft]
  );

  /**
   * 加载草稿
   */
  const loadDraft = useCallback((): QuestionAnswer[] | null => {
    if (!enabled || !sessionId) return null;

    try {
      const savedData = localStorage.getItem(draftKey);
      if (!savedData) return null;

      const draft: DraftData = JSON.parse(savedData);

      // 验证版本和会话ID
      if (draft.version !== DRAFT_VERSION || draft.sessionId !== sessionId) {
        console.warn('⚠️ 草稿版本不匹配或会话ID不同，忽略');
        return null;
      }

      console.log(`📝 加载草稿: ${draft.answers.length} 个答案 (保存于 ${new Date(draft.lastSaved).toLocaleString()})`);
      return draft.answers;
    } catch (error) {
      console.error('❌ 加载草稿失败:', error);
      return null;
    }
  }, [sessionId, enabled, draftKey]);

  /**
   * 清除草稿
   */
  const clearDraft = useCallback(() => {
    try {
      localStorage.removeItem(draftKey);
      console.log('🗑️ 草稿已清除');
    } catch (error) {
      console.error('❌ 清除草稿失败:', error);
    }
  }, [draftKey]);

  /**
   * 检查是否有草稿
   */
  const hasDraft = useCallback((): boolean => {
    try {
      const savedData = localStorage.getItem(draftKey);
      if (!savedData) return false;

      const draft: DraftData = JSON.parse(savedData);
      return draft.version === DRAFT_VERSION && draft.sessionId === sessionId;
    } catch {
      return false;
    }
  }, [sessionId, draftKey]);

  /**
   * 获取草稿保存时间
   */
  const getDraftTimestamp = useCallback((): Date | null => {
    try {
      const savedData = localStorage.getItem(draftKey);
      if (!savedData) return null;

      const draft: DraftData = JSON.parse(savedData);
      return new Date(draft.lastSaved);
    } catch {
      return null;
    }
  }, [draftKey]);

  /**
   * 自动保存效果
   */
  useEffect(() => {
    // 跳过初始挂载（避免覆盖加载的草稿）
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // 只有当有答案时才保存
    if (answers.length > 0) {
      debouncedSave();
    }

    // 清理防抖
    return () => {
      debouncedSave.cancel();
    };
  }, [answers, debouncedSave]);

  return {
    saveDraft,
    loadDraft,
    clearDraft,
    hasDraft,
    getDraftTimestamp
  };
}

/**
 * 🆕 P3优化: 草稿恢复提示组件Props
 */
export interface DraftRestorePromptProps {
  draftTimestamp: Date;
  onRestore: () => void;
  onDiscard: () => void;
}

/**
 * 使用示例：
 *
 * ```tsx
 * function QuestionnairePage() {
 *   const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
 *   const { loadDraft, clearDraft, hasDraft, getDraftTimestamp } = useQuestionnaireDraft(
 *     sessionId,
 *     answers,
 *     true
 *   );
 *
 *   useEffect(() => {
 *     // 检查是否有草稿
 *     if (hasDraft()) {
 *       const timestamp = getDraftTimestamp();
 *       const shouldRestore = confirm(`发现未完成的问卷草稿（保存于 ${timestamp?.toLocaleString()}），是否恢复？`);
 *
 *       if (shouldRestore) {
 *         const draft = loadDraft();
 *         if (draft) {
 *           setAnswers(draft);
 *         }
 *       } else {
 *         clearDraft();
 *       }
 *     }
 *   }, []);
 *
 *   // 提交成功后清除草稿
 *   const handleSubmit = async () => {
 *     await submitAnswers(answers);
 *     clearDraft();
 *   };
 *
 *   return (
 *     // ...问卷组件
 *   );
 * }
 * ```
 */
