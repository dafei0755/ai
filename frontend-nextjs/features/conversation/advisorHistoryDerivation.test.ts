import {
  deriveAdvisorHistoryTitle,
  upsertAdvisorHistoryRecord,
} from './advisorHistoryDerivation';
import type { AdvisorHistoryRecord } from './advisorHistoryPersistence';
import type { ChatMessage } from './types';

describe('advisorHistoryDerivation', () => {
  it('derives the advisor history title from user input before conversation messages', () => {
    const messages: ChatMessage[] = [
      {
        id: 'user-1',
        role: 'user',
        content: 'first message title',
        timestamp: '2026-06-20T00:00:00.000Z',
      },
    ];

    expect(deriveAdvisorHistoryTitle({
      userInput: '  explicit   user input title  ',
      messages,
    })).toBe('explicit user input title');
  });

  it('falls back to the first user message and clamps the title length', () => {
    const messages: ChatMessage[] = [
      {
        id: 'assistant-1',
        role: 'assistant',
        content: 'ignore me',
        timestamp: '2026-06-20T00:00:00.000Z',
      },
      {
        id: 'user-1',
        role: 'user',
        content: 'a very long hometown house conversation title that should be clamped',
        timestamp: '2026-06-20T00:01:00.000Z',
      },
    ];

    expect(deriveAdvisorHistoryTitle({ userInput: '', messages })).toBe(
      'a very long hometown house conversat',
    );
  });

  it('upserts a history record, preserves createdAt, and keeps the newest record first', () => {
    const existing: AdvisorHistoryRecord = {
      sessionId: 'conv-123',
      title: 'Old title',
      createdAt: '2026-06-19T00:00:00.000Z',
      updatedAt: '2026-06-19T00:01:00.000Z',
      modeLabel: '深度思考',
    };
    const other: AdvisorHistoryRecord = {
      sessionId: 'conv-456',
      title: 'Other',
      createdAt: '2026-06-18T00:00:00.000Z',
      updatedAt: '2026-06-18T00:01:00.000Z',
      modeLabel: '方案高参',
    };

    expect(upsertAdvisorHistoryRecord({
      records: [other, existing],
      sessionId: 'conv-123',
      title: 'New title',
      systemMode: 'project',
      now: () => '2026-06-20T00:00:00.000Z',
    })).toEqual([
      {
        sessionId: 'conv-123',
        title: 'New title',
        createdAt: '2026-06-19T00:00:00.000Z',
        updatedAt: '2026-06-20T00:00:00.000Z',
        modeLabel: '方案高参',
      },
      other,
    ]);
  });

  it('returns the existing records when title and mode are unchanged', () => {
    const existing: AdvisorHistoryRecord[] = [
      {
        sessionId: 'conv-123',
        title: 'Same title',
        createdAt: '2026-06-19T00:00:00.000Z',
        updatedAt: '2026-06-19T00:01:00.000Z',
        modeLabel: '深度思考',
      },
    ];

    expect(upsertAdvisorHistoryRecord({
      records: existing,
      sessionId: 'conv-123',
      title: 'Same title',
      systemMode: 'conversation',
      now: () => '2026-06-20T00:00:00.000Z',
    })).toBe(existing);
  });
});
