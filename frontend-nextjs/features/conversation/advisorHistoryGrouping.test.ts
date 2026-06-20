import {
  groupAdvisorHistoryRecords,
  type AdvisorHistoryGroups,
} from './advisorHistoryGrouping';
import type { AdvisorHistoryRecord } from './advisorHistoryPersistence';

const createRecord = (
  sessionId: string,
  updatedAt: string,
): AdvisorHistoryRecord => ({
  sessionId,
  title: sessionId,
  createdAt: updatedAt,
  updatedAt,
  modeLabel: '深度思考',
});

describe('advisorHistoryGrouping', () => {
  it('groups advisor history records into today, last 7 days, and last 30 days', () => {
    const today = createRecord('today', '2026-06-20T08:00:00.000Z');
    const last7Days = createRecord('last7', '2026-06-17T08:00:00.000Z');
    const last30Days = createRecord('last30', '2026-06-01T08:00:00.000Z');
    const older = createRecord('older', '2026-05-01T08:00:00.000Z');

    expect(groupAdvisorHistoryRecords({
      records: [older, last30Days, last7Days, today],
      now: () => new Date('2026-06-20T12:00:00.000Z'),
    })).toEqual<AdvisorHistoryGroups>({
      today: [today],
      last7Days: [last7Days],
      last30Days: [last30Days],
    });
  });

  it('keeps boundary-day records in the inclusive 7-day and 30-day groups', () => {
    const sevenDayBoundary = createRecord('seven-day-boundary', '2026-06-13T00:00:00.000Z');
    const thirtyDayBoundary = createRecord('thirty-day-boundary', '2026-05-21T23:59:59.000Z');

    expect(groupAdvisorHistoryRecords({
      records: [sevenDayBoundary, thirtyDayBoundary],
      now: () => new Date('2026-06-20T12:00:00.000Z'),
    })).toEqual<AdvisorHistoryGroups>({
      today: [],
      last7Days: [sevenDayBoundary],
      last30Days: [thirtyDayBoundary],
    });
  });
});
