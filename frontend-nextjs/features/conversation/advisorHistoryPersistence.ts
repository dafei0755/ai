export type AdvisorHistoryRecord = {
  sessionId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  modeLabel: string;
};

export const ADVISOR_HISTORY_STORAGE_KEY = 'analysis.advisor.history.v1';

type AdvisorHistoryStorage = Pick<Storage, 'getItem' | 'setItem'>;

export function restoreAdvisorHistoryRecords({
  storage,
  onError,
}: {
  storage: AdvisorHistoryStorage;
  onError?: (error: unknown) => void;
}): AdvisorHistoryRecord[] {
  try {
    const raw = storage.getItem(ADVISOR_HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as AdvisorHistoryRecord[]) : [];
  } catch (error) {
    onError?.(error);
    return [];
  }
}

export function persistAdvisorHistoryRecords({
  storage,
  records,
  onError,
}: {
  storage: AdvisorHistoryStorage;
  records: AdvisorHistoryRecord[];
  onError?: (error: unknown) => void;
}): void {
  try {
    storage.setItem(ADVISOR_HISTORY_STORAGE_KEY, JSON.stringify(records));
  } catch (error) {
    onError?.(error);
  }
}
