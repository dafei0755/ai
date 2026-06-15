/**
 * 问卷缓存管理器
 * v7.105: 支持问卷草稿自动保存和恢复
 * 
 * 功能：
 * - 自动保存用户填写的问卷数据到 localStorage
 * - 刷新页面或重新打开时恢复进度
 * - 1小时自动过期机制
 * - 提交成功后自动清除缓存
 */

export interface QuestionnaireCache {
  sessionId: string;              // 会话ID
  step: number;                   // 当前步骤 (1-3)
  confirmedTasks?: any[];         // Step 1 确认的任务
  dimensionValues?: Record<string, number>;  // Step 2 雷达图值
  answers?: Record<string, any>;  // Step 3 答案
  timestamp: number;              // 缓存时间戳
  expiresAt: number;              // 过期时间
}

const CACHE_KEY_PREFIX = 'questionnaire_';
const CACHE_EXPIRY = 60 * 60 * 1000; // 1小时

/**
 * 保存问卷缓存
 * @param sessionId 会话ID
 * @param data 要保存的数据（部分更新）
 */
export function saveQuestionnaireCache(
  sessionId: string,
  data: Partial<QuestionnaireCache>
): void {
  try {
    const key = `${CACHE_KEY_PREFIX}${sessionId}`;
    const existing = getQuestionnaireCache(sessionId);
    
    const cacheData: QuestionnaireCache = {
      sessionId,
      step: data.step || existing?.step || 1,
      confirmedTasks: data.confirmedTasks || existing?.confirmedTasks,
      dimensionValues: data.dimensionValues || existing?.dimensionValues,
      answers: data.answers || existing?.answers,
      timestamp: Date.now(),
      expiresAt: Date.now() + CACHE_EXPIRY
    };
    
    localStorage.setItem(key, JSON.stringify(cacheData));
    console.log(`[QuestionnaireCache] 已保存缓存 - Session: ${sessionId}, Step: ${cacheData.step}`);
  } catch (error) {
    console.error('[QuestionnaireCache] 保存缓存失败:', error);
  }
}

/**
 * 获取问卷缓存
 * @param sessionId 会话ID
 * @returns 缓存数据或 null（如果不存在或已过期）
 */
export function getQuestionnaireCache(sessionId: string): QuestionnaireCache | null {
  try {
    const key = `${CACHE_KEY_PREFIX}${sessionId}`;
    const cached = localStorage.getItem(key);
    
    if (!cached) {
      return null;
    }
    
    const data = JSON.parse(cached) as QuestionnaireCache;
    
    // 检查过期
    if (Date.now() > data.expiresAt) {
      console.log(`[QuestionnaireCache] 缓存已过期 - Session: ${sessionId}`);
      localStorage.removeItem(key);
      return null;
    }
    
    console.log(`[QuestionnaireCache] 加载缓存 - Session: ${sessionId}, Step: ${data.step}`);
    return data;
  } catch (error) {
    console.error('[QuestionnaireCache] 获取缓存失败:', error);
    return null;
  }
}

/**
 * 清除问卷缓存
 * @param sessionId 会话ID
 */
export function clearQuestionnaireCache(sessionId: string): void {
  try {
    const key = `${CACHE_KEY_PREFIX}${sessionId}`;
    localStorage.removeItem(key);
    console.log(`[QuestionnaireCache] 已清除缓存 - Session: ${sessionId}`);
  } catch (error) {
    console.error('[QuestionnaireCache] 清除缓存失败:', error);
  }
}

/**
 * 清除所有过期缓存
 * 建议在应用启动时调用
 */
export function clearExpiredCaches(): void {
  try {
    const now = Date.now();
    let clearedCount = 0;
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(CACHE_KEY_PREFIX)) {
        try {
          const cached = localStorage.getItem(key);
          if (cached) {
            const data = JSON.parse(cached) as QuestionnaireCache;
            if (now > data.expiresAt) {
              localStorage.removeItem(key);
              clearedCount++;
            }
          }
        } catch {
          // 忽略解析错误的缓存项
        }
      }
    }
    
    if (clearedCount > 0) {
      console.log(`[QuestionnaireCache] 已清除 ${clearedCount} 个过期缓存`);
    }
  } catch (error) {
    console.error('[QuestionnaireCache] 清除过期缓存失败:', error);
  }
}
