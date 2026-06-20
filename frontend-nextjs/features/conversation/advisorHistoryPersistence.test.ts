import {
  ADVISOR_HISTORY_STORAGE_KEY,
  persistAdvisorHistoryRecords,
  restoreAdvisorHistoryRecords,
  type AdvisorHistoryRecord,
} from './advisorHistoryPersistence';

const createStorage = (initial: Record<string, string> = {}) => {
  const values = new Map(Object.entries(initial));

  return {
    getItem: jest.fn((key: string) => values.get(key) ?? null),
    setItem: jest.fn((key: string, value: string) => {
      values.set(key, value);
    }),
  };
};

describe('advisorHistoryPersistence', () => {
  it('restores advisor history records from local storage', () => {
    const records: AdvisorHistoryRecord[] = [
      {
        sessionId: 'conv-123',
        title: 'Return home house',
        createdAt: '2026-06-20T00:00:00.000Z',
        updatedAt: '2026-06-20T00:01:00.000Z',
        modeLabel: '深度思考',
      },
    ];
    const storage = createStorage({
      [ADVISOR_HISTORY_STORAGE_KEY]: JSON.stringify(records),
    });

    expect(restoreAdvisorHistoryRecords({ storage })).toEqual(records);
    expect(storage.getItem).toHaveBeenCalledWith(ADVISOR_HISTORY_STORAGE_KEY);
  });

  it('ignores invalid advisor history payloads and reports parse errors', () => {
    const storage = createStorage({
      [ADVISOR_HISTORY_STORAGE_KEY]: '{bad json',
    });
    const onError = jest.fn();

    expect(restoreAdvisorHistoryRecords({ storage, onError })).toEqual([]);
    expect(onError).toHaveBeenCalled();

    const objectStorage = createStorage({
      [ADVISOR_HISTORY_STORAGE_KEY]: JSON.stringify({ sessionId: 'conv-123' }),
    });

    expect(restoreAdvisorHistoryRecords({ storage: objectStorage })).toEqual([]);
  });

  it('persists advisor history records to local storage', () => {
    const storage = createStorage();
    const records: AdvisorHistoryRecord[] = [
      {
        sessionId: 'conv-123',
        title: 'Return home house',
        createdAt: '2026-06-20T00:00:00.000Z',
        updatedAt: '2026-06-20T00:01:00.000Z',
        modeLabel: '深度思考',
      },
    ];

    persistAdvisorHistoryRecords({
      storage,
      records,
    });

    expect(storage.setItem).toHaveBeenCalledWith(
      ADVISOR_HISTORY_STORAGE_KEY,
      JSON.stringify(records),
    );
  });
});
