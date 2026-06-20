import type { AdvisorHistoryRecord } from './advisorHistoryPersistence';

export type AdvisorHistoryGroups = {
  today: AdvisorHistoryRecord[];
  last7Days: AdvisorHistoryRecord[];
  last30Days: AdvisorHistoryRecord[];
};

const startOfLocalDay = (date: Date) =>
  new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();

export function groupAdvisorHistoryRecords({
  records,
  now = () => new Date(),
}: {
  records: AdvisorHistoryRecord[];
  now?: () => Date;
}): AdvisorHistoryGroups {
  const today = startOfLocalDay(now());
  const sevenDaysAgo = today - 7 * 24 * 60 * 60 * 1000;
  const thirtyDaysAgo = today - 30 * 24 * 60 * 60 * 1000;
  const groups: AdvisorHistoryGroups = {
    today: [],
    last7Days: [],
    last30Days: [],
  };

  records.forEach((record) => {
    const normalized = startOfLocalDay(new Date(record.updatedAt));
    if (normalized >= today) {
      groups.today.push(record);
      return;
    }
    if (normalized >= sevenDaysAgo) {
      groups.last7Days.push(record);
      return;
    }
    if (normalized >= thirtyDaysAgo) {
      groups.last30Days.push(record);
    }
  });

  return groups;
}
