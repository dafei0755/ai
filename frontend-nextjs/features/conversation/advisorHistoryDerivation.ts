import type { AdvisorHistoryRecord } from './advisorHistoryPersistence';
import type { ChatMessage } from './types';

export type AdvisorHistorySystemMode = 'conversation' | 'project';

export function deriveAdvisorHistoryTitle({
  userInput,
  messages,
  fallbackTitle = '未命名会话',
  maxLength = 36,
}: {
  userInput: string;
  messages: ChatMessage[];
  fallbackTitle?: string;
  maxLength?: number;
}): string {
  const firstUserMessage = messages.find((message) => message.role === 'user')?.content?.trim();
  const titleSource = userInput.trim() || firstUserMessage || fallbackTitle;
  return titleSource.replace(/\s+/g, ' ').slice(0, maxLength);
}

export function getAdvisorHistoryModeLabel(systemMode: AdvisorHistorySystemMode): string {
  return systemMode === 'project' ? '方案高参' : '深度思考';
}

export function upsertAdvisorHistoryRecord({
  records,
  sessionId,
  title,
  systemMode,
  now = () => new Date().toISOString(),
  limit = 30,
}: {
  records: AdvisorHistoryRecord[];
  sessionId: string;
  title: string;
  systemMode: AdvisorHistorySystemMode;
  now?: () => string;
  limit?: number;
}): AdvisorHistoryRecord[] {
  if (!title) return records;
  const modeLabel = getAdvisorHistoryModeLabel(systemMode);
  const existing = records.find((item) => item.sessionId === sessionId);
  if (existing && existing.title === title && existing.modeLabel === modeLabel) {
    return records;
  }

  const timestamp = now();
  const nextRecord: AdvisorHistoryRecord = {
    sessionId,
    title,
    createdAt: existing?.createdAt ?? timestamp,
    updatedAt: timestamp,
    modeLabel,
  };
  return [
    nextRecord,
    ...records.filter((item) => item.sessionId !== sessionId),
  ].slice(0, limit);
}
