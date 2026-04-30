'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { RefreshCw, Play, Calendar, CheckCircle, AlertCircle, Clock, RotateCcw,
  Database, Globe, TrendingUp, Activity, FileText, AlertTriangle, Search, X } from 'lucide-react';

// ── 数据概览类型 ────────────────────────────────────────────────────────────────
interface SyncHistory {
  id: number; source: string; category?: string;
  started_at: string; completed_at?: string;
  status: 'running' | 'completed' | 'failed';
  projects_total: number; projects_new: number;
  projects_updated: number; projects_failed: number;
  error_message?: string;
}
interface SourceStats {
  source: string; total_projects: number;
  new_today: number; avg_quality_score: number; last_sync: string;
}
interface QualityIssue {
  id: number; project_id: number; issue_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  detected_at: string; resolved_at?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const CRAWLER_API = `${API_BASE}/api/crawler`;

// ── 实时监控类型 ────────────────────────────────────────────────────────────────
interface TaskProgress {
  task_id: string;
  source: string;
  status: string;
  total: number;
  completed: number;
  failed: number;
  progress_percent: number;
  requests_count: number;
  success_rate: number;
  avg_response_time: number;
  current_batch: number;
  total_batches: number;
  current_url: string | null;
  last_error: string | null;
}

interface LogEntry {
  id: number;
  timestamp: string;
  level: string;
  message: string;
  source?: string;  // 爬虫来源标识，无则为全局消息（WS 连接等）
}

// ── APScheduler 任务类型 ────────────────────────────────────────────────────────
interface SchedulerJob {
  id: string;
  name: string;
  trigger_type: string;
  trigger_str: string;
  cron_fields: Record<string, string>;
  next_run_time: string | null;
  status: 'active' | 'paused';
  max_instances: number;
}
interface SchedulerJobsResponse {
  scheduler_running: boolean;
  jobs: SchedulerJob[];
}

// ── 预扫描结果（保留用于兼容旧接口）───────────────────────────────────────────────
interface PreScanCategory {
  name: string;
  url: string;
  db_count: number;
  site_total?: number;  // 来自spider CATEGORY_TOTALS的估算
}
interface PreScanResult {
  source: string;
  categories: PreScanCategory[];
  total_categories: number;
  db_total: number;
  date_range: { earliest: string | null; latest: string | null };
  totals_source?: 'auto' | 'static';  // auto=动态获取成功 static=来自配置文件
  scanned_at: string;
}

// ── 新版：checkpoint + DB + 站点总数状态──────────────────────────────────────────
interface CategoryStatus {
  name: string;
  url: string;
  db_count: number;
  site_total: number | null;
  has_checkpoint: boolean;
  checkpoint_url: string | null;
}
interface SourceStatus {
  enabled?: boolean;
  source: string;
  db_total: number;
  site_total_estimated: number;
  totals_source: 'auto' | 'static';
  last_sync: string | null;
  is_running: boolean;
  checkpoint_count: number;
  total_categories: number;
  categories: CategoryStatus[];
  scanned_at: string;
}

// ── 调度计划类型 ────────────────────────────────────────────────────────────────
interface CategoryStats {
  status: string;
  db_count?: number;
  site_total?: number;  // 站点估算总数
}

interface FullCrawlState {
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string | null;
  completed_at: string | null;
  // 新版扩展字段
  target_categories?: string[] | null;  // 来自预扫描或spider CATEGORIES数量
  total_categories?: number | null;     // 类别总数
  baseline_count?: number | null;       // 开始时 DB 项目数
  scan_at?: string | null;              // 预扫描时间
  categories_done: string[];
  category_stats: Record<string, CategoryStats>;
  total_stats: { total: number; new: number; skipped: number; failed: number };
  error: string | null;
}

interface IncrementalRun {
  run_at: string;
  completed_at: string;
  status: string;
  duration_sec: number;
  new_items: number;
}

interface SourceState {
  full_crawl: FullCrawlState;
  incremental: {
    last_run_at: string | null;
    next_run_at: string | null;
    history: IncrementalRun[];
  };
}

// v2 多数据源格式（v1 兼容单源）
interface ScheduleState {
  exists: boolean;
  version?: number;
  phase: string;
  running_task: string | null;
  // v2 字段
  sources?: Record<string, SourceState>;
  // v1 字段
  full_crawl?: FullCrawlState;
  incremental?: {
    last_run_at: string | null;
    next_run_at: string | null;
    history: IncrementalRun[];
  };
  last_updated: string | null;
  message?: string;
}

// 数据源元数据
const SOURCE_META: Record<string, { label: string; categories: string[]; schedule: string; enabled: boolean; categoryTotals?: Record<string, number> }> = {
  archdaily_cn: {
    label: 'archdaily.cn',
    categories: ['住宅', '文化建筑', '商业建筑', '教育建筑', '办公建筑', '体育建筑', '工业建筑', '基础设施'],
    schedule: '每周一 02:00',
    enabled: true,
  },
  gooood: {
    label: '谷德设计网',
    categories: [
      '商业建筑', '休闲娱乐', '住宅建筑', '文化建筑', '公共空间', '教育建筑',
      '装置艺术', '公共职能建筑', '交通建筑', '绿色建筑', '体育建筑', '综合体',
      '高层建筑', '工业建筑', '中国乡建', '工业建筑改造', '宗教建筑', '园区',
      '医疗建筑', '社区中心', '滨海建筑', '热带建筑', '城市更新', '古建保护',
    ],
    schedule: '每周二02:00',
    enabled: true,
    categoryTotals: {
      '商业建筑': 6169, '休闲娱乐': 5666, '住宅建筑': 5481, '文化建筑': 3545,
      '公共空间': 2140, '教育建筑': 1681, '装置艺术': 1383, '公共职能建筑':  755,
      '交通建筑':  604, '绿色建筑':  558, '体育建筑':  530, '综合体':        527,
      '高层建筑':  389, '工业建筑':  398, '中国乡建':  395, '工业建筑改造':  368,
      '宗教建筑':  348, '园区':      318, '医疗建筑':  269, '社区中心':      265,
      '滨海建筑':  263, '热带建筑':  210, '城市更新':  203, '古建保护':      111,
    },
  },
  dezeen: {
    label: 'Dezeen',
    categories: ['Architecture', 'Interiors', 'Design', 'Landscape', 'Urban Design'],
    schedule: '每周三02:00',
    enabled: false,  // 未实现
  },
};

// ────────────────────────────────────────────────────────────────────────────────
export default function CrawlerMonitorPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'schedule'>('overview');

  // ── 实时监控 状态 ────────────────────────────────────────────────────────────
  const [connected, setConnected] = useState(false);
  const [tasks, setTasks] = useState<Record<string, TaskProgress>>({});
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 从 localStorage 恢复的日志已有 id，初始化计数器从 max+1 开始避免 key 碰撞
  const logIdRef = useRef<number>((() => {
    try {
      const saved = typeof window !== 'undefined' ? localStorage.getItem('crawler_sched_logs') : null;
      if (saved) {
        const arr = JSON.parse(saved) as LogEntry[];
        if (arr.length > 0) return Math.max(...arr.map(l => l.id)) + 1;
      }
    } catch { /* ignore */ }
    return 0;
  })());
  const logsEndRef = useRef<HTMLDivElement>(null);

  // ── 调度计划 状态 ────────────────────────────────────────────────────────────
  const [scheduleState, setScheduleState] = useState<ScheduleState | null>(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string>('archdaily_cn');
  const schedPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── 新版 source-status 状态 ──────────────────────────────────────────────────
  const [sourceStatus, setSourceStatus] = useState<SourceStatus | null>(null);
  const [sourceStatusLoading, setSourceStatusLoading] = useState(false);
  const [syncing, setSyncing] = useState<'sync' | 'reset-sync' | null>(null);

  // ── 调度Tab 实时进度日志（localStorage 持久化）─────────────────────────────────────
  const SCHED_LOGS_KEY = 'crawler_sched_logs';
  const [schedLogs, setSchedLogsRaw] = useState<LogEntry[]>(() => {
    try {
      const saved = typeof window !== 'undefined' ? localStorage.getItem(SCHED_LOGS_KEY) : null;
      return saved ? (JSON.parse(saved) as LogEntry[]) : [];
    } catch { return []; }
  });
  const setSchedLogs = useCallback((updater: LogEntry[] | ((prev: LogEntry[]) => LogEntry[])) => {
    setSchedLogsRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      try { localStorage.setItem(SCHED_LOGS_KEY, JSON.stringify(next.slice(-200))); } catch { /* quota */ }
      return next;
    });
  }, []);
  const schedLogsEndRef = useRef<HTMLDivElement>(null);
  const [showSchedLogs, setShowSchedLogs] = useState(() => {
    try { return typeof window !== 'undefined' && localStorage.getItem('crawler_sched_logs_open') === '1'; }
    catch { return false; }
  });

  // ── APScheduler 任务 状态 ────────────────────────────────────────────────────
  const [jobsData, setJobsData] = useState<SchedulerJobsResponse | null>(null);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobAction, setJobAction] = useState<string | null>(null);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [editCron, setEditCron] = useState<{ day_of_week?: string; hour?: number; minute?: number }>({});

  // ── 数据概览 状态 ──────────────────────────────────────────────────────────
  const [syncHistory, setSyncHistory] = useState<SyncHistory[]>([]);
  const [sourceStats, setSourceStats] = useState<SourceStats[]>([]);
  const [qualityIssues, setQualityIssues] = useState<QualityIssue[]>([]);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewLastRefresh, setOverviewLastRefresh] = useState<Date | null>(null);

  // ── 日志 工具 ────────────────────────────────────────────────────────────────
  const addLog = useCallback((level: string, message: string) => {
    const entry: LogEntry = {
      id: logIdRef.current++,
      timestamp: new Date().toLocaleTimeString('zh-CN'),
      level, message,
    };
    setLogs(prev => {
      const next = [...prev, entry];
      return next.length > 200 ? next.slice(-200) : next;
    });
  }, []);

  // ── WebSocket连接────────────────────────────────────────────────────────────
  useEffect(() => {
    function connect() {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = new URL(API_BASE).host;
      const ws = new WebSocket(`${wsProtocol}//${wsHost}/api/crawler/ws/monitor`);
      const addSchedLog = (level: string, message: string, src?: string) => {
        const entry: LogEntry = { id: logIdRef.current++, timestamp: new Date().toLocaleTimeString('zh-CN'), level, message, source: src };
        setSchedLogs(prev => { const next = [...prev, entry]; return next.length > 200 ? next.slice(-200) : next; });
      };
      ws.onopen = () => {
        setConnected(true);
        addLog('info', 'WebSocket连接成功');
        addSchedLog('info', 'WebSocket 已连接，等待爬虫事件...');  // 无 source → 所有源都显示
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'initial_state') {
          const initial: Record<string, TaskProgress> = {};
          data.data.forEach((t: TaskProgress) => { initial[t.task_id] = t; });
          setTasks(initial);
          if (data.data.length > 0) {
            addSchedLog('info', `恢复 ${data.data.length} 个任务状态`);
          }
        } else if (data.type === 'progress') {
          setTasks(prev => ({ ...prev, [data.data.task_id]: data.data }));
          const t: TaskProgress = data.data;
          const msg = t.current_url
            ? `[${t.source ?? t.task_id}] ${t.current_url}`
            : `[${t.source ?? t.task_id}] ${t.completed}/${t.total} (${t.progress_percent.toFixed(1)}%) 批次${t.current_batch}/${t.total_batches}`;
          addSchedLog('info', msg, t.source ?? undefined);
        } else if (data.type === 'log') {
          addLog(data.data.level, data.data.message);
          addSchedLog(data.data.level, data.data.message, data.data.source ?? undefined);
        }
      };
      ws.onerror = () => {
        addLog('error', 'WebSocket连接错误');
        addSchedLog('error', 'WebSocket 连接出错');
      };
      ws.onclose = () => {
        setConnected(false);
        addLog('warning', 'WebSocket断开，5秒后重连');
        addSchedLog('warning', 'WebSocket 断开，5s 后重连...');
        reconnectRef.current = setTimeout(connect, 5000);
      };
      wsRef.current = ws;
    }
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [addLog]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    if (showSchedLogs) schedLogsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    try { localStorage.setItem('crawler_sched_logs_open', showSchedLogs ? '1' : '0'); } catch { /* ignore */ }
  }, [schedLogs, showSchedLogs]);

  // 有活动任务时自动展开日志面板
  useEffect(() => {
    const running = Object.values(tasks).some(t => t.status === 'running');
    if (running) {
      setShowSchedLogs(true);
      try { localStorage.setItem('crawler_sched_logs_open', '1'); } catch { /* ignore */ }
    }
  }, [tasks]);

  // ── 获取调度状态 ──────────────────────────────────────────────────────────────
  const fetchSchedule = useCallback(async () => {
    try {
      const res = await fetch(`${CRAWLER_API}/schedule`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ScheduleState = await res.json();
      setScheduleState(data);
    } catch (e) {
      console.error('获取调度状态失败', e);
    }
  }, []);

  // ── 获取数据源checkpoint状态 ──────────────────────────────────────────────────
  const fetchSourceStatus = useCallback(async (src?: string) => {
    const target = src ?? selectedSource;
    setSourceStatusLoading(true);
    try {
      const res = await fetch(`${CRAWLER_API}/schedule/source-status?source=${encodeURIComponent(target)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSourceStatus(await res.json());
    } catch (e) {
      console.error('获取源状态失败', e);
    } finally {
      setSourceStatusLoading(false);
    }
  }, [selectedSource]);

  // 切 Tab 时加载source状态，5秒轮询
  useEffect(() => {
    if (activeTab === 'schedule') {
      setScheduleLoading(true);
      Promise.all([fetchSchedule(), fetchSourceStatus()]).finally(() => setScheduleLoading(false));
    }
  }, [activeTab, fetchSchedule, fetchSourceStatus]);

  useEffect(() => {
    const isRunning = sourceStatus?.is_running || (scheduleState?.phase && scheduleState.phase !== 'idle');
    if (isRunning) {
      schedPollRef.current = setInterval(() => {
        fetchSchedule();
        fetchSourceStatus();
      }, 5000);
    } else {
      if (schedPollRef.current) clearInterval(schedPollRef.current);
    }
    return () => { if (schedPollRef.current) clearInterval(schedPollRef.current); };
  }, [sourceStatus?.is_running, scheduleState?.phase, fetchSchedule, fetchSourceStatus]);

  // 切数据源时刷新状态，同时清除上一个源的提示信息
  useEffect(() => {
    if (activeTab === 'schedule') fetchSourceStatus(selectedSource);
    setTriggerMsg(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSource]);

  // ── 立即同步（按checkpoint继续爬取）─────────────────────────────────────────
  async function triggerSync(source: string = selectedSource) {
    setSyncing('sync');
    setTriggerMsg(null);
    try {
      const res = await fetch(`${CRAWLER_API}/schedule/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'incremental', source }),
      });
      const data = await res.json();
      setTriggerMsg(data.message || data.status);
      // 快速轮询 5 次让两 Tab 尽快感知到 running 状态
      [2000, 4000, 7000, 12000, 20000].forEach(d =>
        setTimeout(() => { fetchSchedule(); fetchSourceStatus(source); if (activeTab === 'overview') fetchOverview(); }, d)
      );
    } catch (e) {
      setTriggerMsg(`错误: ${e}`);
    } finally {
      setSyncing(null);
    }
  }

  // ── 清空 checkpoint 并全量爬取 ───────────────────────────────────────────────
  async function resetCheckpointAndSync(source: string = selectedSource) {
    const label = SOURCE_META[source]?.label ?? source;
    if (!confirm(`确定要清空 ${label} 的所有 checkpoint 数据，从头开始重新爬取所有分类吗？`)) return;
    setSyncing('reset-sync');
    setTriggerMsg(null);
    try {
      // Step 1: 清空 checkpoint
      const resetRes = await fetch(
        `${CRAWLER_API}/schedule/reset-checkpoint?source=${encodeURIComponent(source)}`,
        { method: 'POST' },
      );
      if (!resetRes.ok) throw new Error(`清空 checkpoint 失败 HTTP ${resetRes.status}`);
      const resetData = await resetRes.json();
      // Step 2: 触发全量爬取
      const trigRes = await fetch(`${CRAWLER_API}/schedule/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'full', source }),
      });
      const trigData = await trigRes.json();
      setTriggerMsg(`已清空 ${resetData.cleared} 个 checkpoint，重新爬取已启动 ${trigData.message ?? ''}`);
      [2000, 4000, 7000, 12000, 20000].forEach(d =>
        setTimeout(() => { fetchSchedule(); fetchSourceStatus(source); if (activeTab === 'overview') fetchOverview(); }, d)
      );
    } catch (e) {
      setTriggerMsg(`错误: ${e}`);
    } finally {
      setSyncing(null);
    }
  }

  // ── APScheduler 任务获取 ──────────────────────────────────────────────────────
  const fetchJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const res = await fetch(`${CRAWLER_API}/jobs`);
      if (res.ok) setJobsData(await res.json());
    } catch (e) {
      console.error('获取定时任务失败:', e);
    } finally {
      setJobsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'schedule') fetchJobs();
  }, [activeTab, fetchJobs]);

  // ── 数据概览 加载 ──────────────────────────────────────────────────────────
  const overviewHeaders = useCallback(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('wp_jwt_token') : null;
    return { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) };
  }, []);

  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const headers = overviewHeaders();
      const [histRes, statsRes, issuesRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/external/sync-history?limit=10`, { headers }),
        fetch(`${API_BASE}/api/external/source-stats`, { headers }),
        fetch(`${API_BASE}/api/external/quality-issues?resolved=false&limit=20`, { headers }),
      ]);
      if (histRes.status === 'fulfilled' && histRes.value.ok)
        setSyncHistory((await histRes.value.json()).history || []);
      if (statsRes.status === 'fulfilled' && statsRes.value.ok)
        setSourceStats((await statsRes.value.json()).stats || []);
      if (issuesRes.status === 'fulfilled' && issuesRes.value.ok)
        setQualityIssues((await issuesRes.value.json()).issues || []);
      setOverviewLastRefresh(new Date());
    } catch (e) { console.error('获取概览数据失败:', e); }
    finally { setOverviewLoading(false); }
  }, [overviewHeaders]);

  // 数据概览：有运行中任务时自动每 5s 刷新
  const overviewPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (activeTab === 'overview') fetchOverview();  // 切换时立即加载
  }, [activeTab, fetchOverview]);
  useEffect(() => {
    const hasRunning = syncHistory.some(s => s.status === 'running');
    if (hasRunning && activeTab === 'overview') {
      overviewPollRef.current = setInterval(fetchOverview, 5000);
    } else {
      if (overviewPollRef.current) clearInterval(overviewPollRef.current);
    }
    return () => { if (overviewPollRef.current) clearInterval(overviewPollRef.current); };
  }, [syncHistory, activeTab, fetchOverview]);

  const overviewFormatTime = (iso: string) => {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60) return `${diff}秒前`;
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    return `${Math.floor(diff / 86400)}天前`;
  };
  const overviewStatusColor = (s: string) => ({
    completed: 'bg-green-100 text-green-800', running: 'bg-blue-100 text-blue-800',
    failed: 'bg-red-100 text-red-800'
  }[s] ?? 'bg-gray-100 text-gray-800');
  const severityColor = (s: string) => ({
    critical: 'bg-red-100 text-red-800', high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800', low: 'bg-blue-100 text-blue-800'
  }[s] ?? 'bg-gray-100 text-gray-800');

  async function jobControlAction(action: 'pause' | 'resume' | 'run-now', jobId: string) {
    setJobAction(`${action}:${jobId}`);
    try {
      const res = await fetch(`${CRAWLER_API}/jobs/${encodeURIComponent(jobId)}/${action}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchJobs();
      setTriggerMsg(`操作成功(${action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : '立即执行'}): ${jobId}`);
    } catch (e) {
      setTriggerMsg(`操作失败: ${e}`);
    } finally {
      setJobAction(null);
    }
  }

  async function saveJobCron(jobId: string) {
    setJobAction(`cron:${jobId}`);
    try {
      const body: Record<string, unknown> = {};
      if (editCron.day_of_week !== undefined) body.day_of_week = editCron.day_of_week;
      if (editCron.hour !== undefined) body.hour = editCron.hour;
      if (editCron.minute !== undefined) body.minute = editCron.minute;
      const res = await fetch(`${CRAWLER_API}/jobs/${encodeURIComponent(jobId)}/cron`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchJobs();
      setEditingJobId(null);
      setEditCron({});
      setTriggerMsg('Cron 已更新');
    } catch (e) {
      setTriggerMsg(`操作失败: ${e}`);
    } finally {
      setJobAction(null);
    }
  }

  // ── 爬虫控制 ──────────────────────────────────────────────────────────────────
  async function apiCall(endpoint: string, method = 'GET', body?: unknown) {
    const options: RequestInit = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) options.body = JSON.stringify(body);
    return (await fetch(`${CRAWLER_API}${endpoint}`, options)).json();
  }
  // ── 计算值 ──────────────────────────────────────────────────────────────────
  const activeTaskCount = Object.values(tasks).filter(t => t.status === 'running').length;

  const statusColor: Record<string, string> = {
    running: 'bg-green-100 text-green-800', paused: 'bg-yellow-100 text-yellow-800',
    stopped: 'bg-gray-100 text-gray-800', error: 'bg-red-100 text-red-800', idle: 'bg-blue-100 text-blue-800',
  };
  const logColor: Record<string, string> = {
    info: 'text-blue-400', warning: 'text-yellow-400', error: 'text-red-400',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">爬虫监控中心</h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100 text-sm">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-gray-600">{connected ? 'WS' : '断线'}</span>
            {activeTaskCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-blue-600 text-white text-xs font-bold rounded-full">{activeTaskCount}</span>
            )}
          </div>
          {activeTab === 'schedule' && scheduleState?.phase && scheduleState.phase !== 'idle' && (
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-100 text-blue-700 text-sm font-medium animate-pulse">
              <RefreshCw size={13} className="animate-spin" /> 运行中
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {(['overview', 'schedule'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'overview' ? '📊 数据概览' : '⚙️ 调度计划'}
          </button>
        ))}
      </div>

      {/* ═══ 数据概览 Tab ═══ */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* 顶栏 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Database className="w-4 h-4 text-blue-600" />
              <span>统计各数据源元数据</span>
              {overviewLastRefresh && <span>· 刷新于 {overviewFormatTime(overviewLastRefresh.toISOString())}</span>}
            </div>
            <button
              onClick={fetchOverview} disabled={overviewLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
            >
              <RefreshCw className={`w-4 h-4 ${overviewLoading ? 'animate-spin' : ''}`} /> 刷新
            </button>
          </div>

          {/* 数据源卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(sourceStats.length > 0 ? sourceStats : Object.keys(SOURCE_META).map(k => ({
              source: k, total_projects: 0, new_today: 0, avg_quality_score: 0,
              last_sync: new Date().toISOString(),
            }))).map(stat => (
              <div key={stat.source} className="bg-white rounded-xl shadow-sm border p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <Globe className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 text-sm">
                        {SOURCE_META[stat.source]?.label ?? stat.source}
                      </h3>
                      <p className="text-xs text-gray-500">{SOURCE_META[stat.source]?.schedule}</p>
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500 text-sm">已抓取</span>
                    <span className="font-bold text-lg text-gray-900">{stat.total_projects.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500 text-sm">今日新增</span>
                    <span className="flex items-center gap-1 text-green-600 font-semibold text-sm">
                      <TrendingUp className="w-3.5 h-3.5" />+{stat.new_today}
                    </span>
                  </div>
                  {stat.avg_quality_score > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-500 text-sm">质量评分</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-blue-500 to-green-500 rounded-full"
                            style={{ width: `${stat.avg_quality_score * 100}%` }} />
                        </div>
                        <span className="text-sm font-semibold">{(stat.avg_quality_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* 同步历史 */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="px-5 py-3 border-b flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <h2 className="font-semibold text-gray-900 text-sm">同步历史（最近10条）</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['状态', '数据源', '分类', '开始时间', '耗时', '总数', '新增/更新', '失败'].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {syncHistory.map(s => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${overviewStatusColor(s.status)}`}>
                          {s.status === 'completed' ? '完成' : s.status === 'running' ? '运行中' : '失败'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900 capitalize">{s.source}</td>
                      <td className="px-4 py-3 text-gray-500">{s.category || '-'}</td>
                      <td className="px-4 py-3 text-gray-500">{overviewFormatTime(s.started_at)}</td>
                      <td className="px-4 py-3 text-gray-500">
                        {s.completed_at ? `${Math.round((new Date(s.completed_at).getTime() - new Date(s.started_at).getTime()) / 1000)}s` : '-'}
                      </td>
                      <td className="px-4 py-3 font-medium">{s.projects_total}</td>
                      <td className="px-4 py-3">
                        <span className="text-green-600 font-semibold">+{s.projects_new}</span>
                        {' / '}
                        <span className="text-blue-600">{s.projects_updated}</span>
                      </td>
                      <td className="px-4 py-3">
                        {s.projects_failed > 0
                          ? <span className="text-red-600 font-semibold">{s.projects_failed}</span>
                          : <span className="text-gray-400">0</span>}
                      </td>
                    </tr>
                  ))}
                  {syncHistory.length === 0 && (
                    <tr><td colSpan={8} className="px-4 py-10 text-center text-gray-400 text-sm">暂无同步记录</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 质量问题 */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="px-5 py-3 border-b flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              <h2 className="font-semibold text-gray-900 text-sm">数据质量问题（未解决）</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['严重程度', '问题类型', '项目ID', '发现时间', '操作'].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {qualityIssues.map(issue => (
                    <tr key={issue.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${severityColor(issue.severity)}`}>
                          {({ critical: '严重', high: '高', medium: '中', low: '低' }[issue.severity]) ?? issue.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {({ missing_description: '缺少描述', low_quality_description: '低质量描述', missing_images: '缺少图片' }[issue.issue_type]) ?? issue.issue_type}
                      </td>
                      <td className="px-4 py-3"><code className="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-mono">{issue.project_id}</code></td>
                      <td className="px-4 py-3 text-gray-500">{overviewFormatTime(issue.detected_at)}</td>
                      <td className="px-4 py-3"><button className="text-blue-600 hover:text-blue-800 text-xs font-medium">查看</button></td>
                    </tr>
                  ))}
                  {qualityIssues.length === 0 && (
                    <tr><td colSpan={5} className="px-4 py-10 text-center text-gray-400 text-sm">
                      <div className="flex flex-col items-center gap-2">
                        <CheckCircle className="w-8 h-8 text-green-500" /><span>暂无质量问题</span>
                      </div>
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 相关文档 */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <FileText className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-gray-900 text-sm mb-1">相关文档</p>
                <ul className="space-y-1 text-sm">
                  <li><a href="/LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md" className="text-blue-600 hover:underline">大规模外部数据架构说明</a></li>
                  <li><a href="/EXTERNAL_DATA_STORAGE_GUIDE.md" className="text-blue-600 hover:underline">外部数据存储指南</a></li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══ 调度计划 Tab ═══ */}
      {activeTab === 'schedule' && (
        <div className="space-y-5">

          {/* 数据源选择 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">数据源:</span>
            <div className="flex gap-1 bg-gray-100 p-0.5 rounded-lg">
              {Object.entries(SOURCE_META).map(([key, meta]) => (
                <button
                  key={key}
                  onClick={() => meta.enabled ? setSelectedSource(key) : undefined}
                  disabled={!meta.enabled}
                  title={!meta.enabled ? `${meta.label} 未启用` : meta.label}
                  className={`relative px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    !meta.enabled
                      ? 'text-gray-300 cursor-not-allowed'
                      : selectedSource === key
                        ? 'bg-white shadow text-gray-900'
                        : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {meta.label}{!meta.enabled && <span className="ml-1 text-gray-300">(停用)</span>}
                </button>
              ))}
            </div>
            <button
              onClick={() => fetchSourceStatus(selectedSource)}
              disabled={sourceStatusLoading}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
              title="刷新状态"
            >
              <RefreshCw size={13} className={sourceStatusLoading ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* 调度器未运行提示 */}
          {(!scheduleState?.exists) && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
              <strong>⚠️ 调度器未运行</strong> 功能受限。请通过以下命令启动:
              <code className="ml-2 bg-amber-100 px-2 py-0.5 rounded font-mono">python scripts/crawl_scheduler.py daemon</code>
              <br />手动测试可通过下方 API 触发按钮
            </div>
          )}

          {/* ─── 状态卡片 + 操作按钮 ─── */}
          <div className="bg-white rounded-xl shadow-sm border p-5 space-y-4">
            {/* 标题 */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-gray-900">
                  {SOURCE_META[selectedSource]?.label ?? selectedSource}
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  定时任务：{SOURCE_META[selectedSource]?.schedule}
                  {sourceStatus?.totals_source === 'auto' && (
                    <span className="ml-2 px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium">
                      实时数据
                    </span>
                  )}
                </p>
              </div>
              {sourceStatus?.is_running && (
                <span className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium animate-pulse">
                  <RefreshCw size={12} className="animate-spin" /> 同步中
                </span>
              )}
            </div>

            {/* 统计数字 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-gray-900">
                  {sourceStatus ? sourceStatus.db_total.toLocaleString() : '—'}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">DB 项目数</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-blue-700">
                  {sourceStatus?.site_total_estimated
                    ? `~${(sourceStatus.site_total_estimated / 1000).toFixed(0)}k`
                    : '—'}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">站点估算</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-gray-900">
                  {sourceStatus
                    ? `${sourceStatus.checkpoint_count} / ${sourceStatus.total_categories}`
                    : '—'}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">Checkpoint</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-sm font-semibold text-gray-700 leading-tight">
                  {sourceStatus?.last_sync
                    ? new Date(sourceStatus.last_sync).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : '从未同步'}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">最后同步</p>
              </div>
            </div>

            {/* 数据源禁用提示 */}
            {sourceStatus?.enabled === false && (
              <div className="flex items-start gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                <span className="flex-shrink-0 mt-0.5">⚠️</span>
                <span>该数据源暂未开放，需先完成 <strong>archdaily.cn</strong> 全量爬取后才能启用。如需强制启用，请修改后端 <code className="font-mono text-xs bg-amber-100 px-1 rounded">scripts/crawl_scheduler.py</code> 中的 <code className="font-mono text-xs bg-amber-100 px-1 rounded">enabled: True</code>。</span>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                onClick={() => triggerSync(selectedSource)}
                disabled={!!syncing || !!sourceStatus?.is_running || sourceStatus?.enabled === false}
                className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              >
                {syncing === 'sync'
                  ? <><RefreshCw size={14} className="animate-spin" /> 同步中..</>
                  : <><Play size={14} /> 立即同步</>
                }
              </button>
              <button
                onClick={() => resetCheckpointAndSync(selectedSource)}
                disabled={!!syncing || !!sourceStatus?.is_running || sourceStatus?.enabled === false}
                title="清空 checkpoint 数据，重新从第1页爬取所有分类"
                className="flex items-center gap-2 px-4 py-2.5 bg-orange-50 text-orange-700 border border-orange-200 rounded-lg hover:bg-orange-100 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              >
                {syncing === 'reset-sync'
                  ? <><RefreshCw size={14} className="animate-spin" /> 操作中..</>
                  : <><RotateCcw size={14} /> 清空并重新爬取</>
                }
              </button>
            </div>

            {/* 说明 */}
            <p className="text-xs text-gray-400 leading-relaxed">
              「立即同步」按 checkpoint 继续爬取，遇到已有 URL 时自动停止。
              「清空并重新爬取」将清除进度记录，从每个分类第1页重新开始（适用于首次爬取或结构调整后）。
            </p>
          </div>

          {/* ─── 实时进度面板 — 有任务或有日志就显示 ─── */}
          {(() => {
            const allActiveTasks = Object.values(tasks).filter(t => t.status === 'running' || t.status === 'paused');
            const isActive = sourceStatus?.is_running || syncing !== null || allActiveTasks.length > 0 || triggerMsg !== null;
            // 无任务且无日志时显示占位提示
            if (!isActive && schedLogs.length === 0) return (
              <div className="flex items-center gap-2 px-4 py-3 bg-white rounded-xl border border-dashed border-gray-200 text-sm text-gray-400">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-300 flex-shrink-0" />
                点击「立即同步」后，实时进度将在此显示
              </div>
            );
            return (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
                {/* 面板标题栏 */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-700">实时进度</span>
                    {allActiveTasks.length > 0 && (
                      <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse inline-block" />
                        运行中
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    {allActiveTasks.length > 0 && <span>{allActiveTasks.length} 个任务</span>}
                    {schedLogs.length > 0 && (
                      <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded-full font-medium">
                        {schedLogs.length} 条日志
                      </span>
                    )}
                  </div>
                </div>

                {/* 启动中占位 */}
                {allActiveTasks.length === 0 && (syncing !== null || triggerMsg !== null) && (
                  <div className="px-5 py-4 flex items-center gap-3 border-b border-gray-100">
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
                    <span className="text-sm text-gray-600">{triggerMsg ?? '正在启动任务...'}</span>
                  </div>
                )}

                {/* 任务列表 */}
                {allActiveTasks.map(task => {
                  let categorySlug: string | null = null;
                  let urlObj: URL | null = null;
                  try {
                    urlObj = new URL(task.current_url ?? '');
                    const parts = urlObj.pathname.split('/').filter(Boolean);
                    const slug = parts.filter(p => p !== 'page' && !/^\d+$/.test(p)).pop();
                    categorySlug = slug ?? null;
                  } catch { /* ignore */ }
                  const pageNum = (() => {
                    if (!urlObj) return null;
                    const parts = urlObj.pathname.split('/');
                    const pi = parts.indexOf('page');
                    return pi !== -1 && parts[pi + 1] ? Number(parts[pi + 1]) : null;
                  })();
                  return (
                    <div key={task.task_id} className="px-5 py-4 border-b border-gray-100">
                      {/* 任务头部 */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                            task.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-yellow-400'
                          }`} />
                          <span className="text-xs font-medium px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">
                            {task.source ?? task.task_id.split('_')[0]}
                          </span>
                          <span className="text-xs text-gray-500">批次 {task.current_batch}/{task.total_batches}</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs tabular-nums">
                          <span className="text-gray-900 font-semibold">{task.completed.toLocaleString()}</span>
                          <span className="text-gray-400">/ {task.total.toLocaleString()}</span>
                          <span className="text-gray-500">成功率 <span className="text-green-600 font-medium">{(task.success_rate * 100).toFixed(0)}%</span></span>
                          {task.failed > 0 && <span className="text-red-500 font-medium">失败 {task.failed}</span>}
                        </div>
                      </div>

                      {/* 进度条 */}
                      <div className="w-full bg-gray-100 rounded-full h-1.5 mb-3">
                        <div
                          className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
                          style={{ width: `${task.progress_percent}%` }}
                        />
                      </div>

                      {/* 当前目录 */}
                      {categorySlug && (
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs text-gray-400 flex-shrink-0">目录</span>
                          <span className="text-sm font-semibold text-orange-600 truncate">
                            {categorySlug.replace(/-/g, ' ')}
                          </span>
                          {pageNum !== null && (
                            <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded flex-shrink-0">P{pageNum}</span>
                          )}
                        </div>
                      )}

                      {/* 当前 URL */}
                      {task.current_url && (
                        <div className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2">
                          <div className="text-[10px] text-gray-400 mb-0.5 font-medium uppercase tracking-wide">当前访问</div>
                          <span className="font-mono text-xs text-blue-600 break-all leading-relaxed">
                            {task.current_url}
                          </span>
                        </div>
                      )}

                      {/* 错误 */}
                      {task.last_error && (
                        <div className="mt-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                          <span className="text-xs text-red-600 break-all">⚠️ {task.last_error}</span>
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* 日志折叠栏 */}
                <div
                  className="flex items-center justify-between px-5 py-2.5 cursor-pointer hover:bg-gray-50 select-none border-t border-gray-100"
                  onClick={() => setShowSchedLogs(v => !v)}
                >
                  <span className="text-sm font-medium text-gray-600">日志记录</span>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={e => { e.stopPropagation(); setSchedLogs([]); try { localStorage.removeItem('crawler_sched_logs'); } catch { /* ignore */ } }}
                      className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                    >清空</button>
                    <span className="text-gray-400 text-xs">{showSchedLogs ? '▲' : '▼'}</span>
                  </div>
                </div>

                {/* 日志内容 */}
                {showSchedLogs && (
                  <div className="border-t border-gray-100 bg-gray-950 max-h-72 overflow-y-auto px-5 py-3 font-mono text-[13px] leading-loose space-y-1.5">
                    {(() => {
                      // 过滤：显示当前数据源的日志，以及无 source 的全局消息（WS 连接等）
                      const filtered = schedLogs.filter(log => !log.source || log.source === selectedSource);
                      return filtered.length === 0 ? (
                        <p className="text-gray-300 py-1">等待日志...</p>
                      ) : filtered.map(log => (
                        <div key={log.id} className="flex gap-2">
                          <span className="text-gray-300 whitespace-nowrap flex-shrink-0">[{log.timestamp}]</span>
                          <span className={`w-12 flex-shrink-0 font-bold ${
                            log.level === 'error' ? 'text-red-300' :
                            log.level === 'warning' ? 'text-yellow-200' :
                            log.level === 'info' ? 'text-sky-200' : 'text-gray-200'
                          }`}>{log.level.slice(0,4).toUpperCase()}</span>
                          <span className="text-white break-all">{log.message}</span>
                        </div>
                      ));
                    })()
                    }
                    <div ref={schedLogsEndRef} />
                  </div>
                )}
              </div>
            );
          })()}

          {/* ─── 分类进度列表 ─── */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="px-5 py-3 border-b bg-gray-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database size={14} className="text-gray-500" />
                <span className="text-sm font-semibold text-gray-700">
                  分类进度
                  {sourceStatus && (
                    <span className="ml-2 text-xs font-normal text-gray-400">
                      {sourceStatus.total_categories} 个分类
                      {sourceStatus.checkpoint_count > 0 && (
                        <span className="ml-1 text-green-600">· {sourceStatus.checkpoint_count} 个 checkpoint</span>
                      )}
                    </span>
                  )}
                </span>
              </div>
              {sourceStatus && sourceStatus.db_total > 0 && sourceStatus.site_total_estimated > 0 && (
                <span className="text-xs text-gray-500">
                  进度: {Math.min(100, Math.round(sourceStatus.db_total / sourceStatus.site_total_estimated * 100))}%
                </span>
              )}
            </div>

            {sourceStatusLoading && !sourceStatus && (
              <div className="px-5 py-6 text-center text-gray-400 text-sm">加载中..</div>
            )}

            {/* 有 API 数据时显示完整进度；无数据时用静态分类列表兜底 */}
            {sourceStatus ? (
              <div className="divide-y divide-gray-50">
                {sourceStatus.categories.map(cat => {
                  const pct = cat.site_total ? Math.min(100, Math.round(cat.db_count / cat.site_total * 100)) : null;
                  return (
                    <div key={cat.name} className="flex items-center justify-between px-5 py-2.5 hover:bg-gray-50">
                      {/* 左侧：checkpoint 圆点 + 分类名 */}
                      <div className="flex items-center gap-2.5">
                        <div
                          title={cat.has_checkpoint ? `有checkpoint: ${cat.checkpoint_url ?? ''}` : '无checkpoint，将从头开始'}
                          className={`w-2 h-2 flex-shrink-0 rounded-full ${cat.has_checkpoint ? 'bg-green-500' : 'bg-gray-300'}`}
                        />
                        <span className={`text-sm ${cat.has_checkpoint ? 'text-gray-800' : 'text-gray-500'}`}>
                          {cat.name}
                        </span>
                      </div>
                      {/* 右侧：进度条 + 数量 */}
                      <div className="flex items-center gap-3">
                        {pct !== null && (
                          <div className="flex items-center gap-1.5">
                            <div className="w-20 bg-gray-200 rounded-full h-1.5">
                              <div
                                className={`h-1.5 rounded-full ${pct >= 100 ? 'bg-green-500' : pct > 50 ? 'bg-blue-500' : 'bg-orange-400'}`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-400 w-8 text-right">{pct}%</span>
                          </div>
                        )}
                        <span className="text-xs text-gray-500 tabular-nums min-w-[7rem] text-right">
                          {cat.db_count.toLocaleString()}
                          {cat.site_total != null ? ` / ${cat.site_total.toLocaleString()}` : ''}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : !sourceStatusLoading && (
              /* 静态兜底：显示分类名，无进度数据 */
              <div className="divide-y divide-gray-50">
                {(SOURCE_META[selectedSource]?.categories ?? []).map(name => {
                  const staticTotal = SOURCE_META[selectedSource]?.categoryTotals?.[name];
                  return (
                    <div key={name} className="flex items-center justify-between px-5 py-2.5 hover:bg-gray-50">
                      <div className="flex items-center gap-2.5">
                        <div className="w-2 h-2 flex-shrink-0 rounded-full bg-gray-200" title="点击刷新加载进度" />
                        <span className="text-sm text-gray-500">{name}</span>
                      </div>
                      <span className="text-xs text-gray-400 tabular-nums">
                        {staticTotal != null ? `/ ${staticTotal.toLocaleString()}` : ''}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* ─── APScheduler 定时任务 ─── */}
          <div className="bg-white rounded-xl shadow-sm border p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                <Calendar size={16} className="text-purple-500" /> APScheduler 定时任务
              </h2>
              <div className="flex items-center gap-2">
                {jobsData !== null && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    jobsData.scheduler_running ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {jobsData.scheduler_running ? '运行中' : '未运行'}
                  </span>
                )}
                <button
                  onClick={fetchJobs}
                  disabled={jobsLoading}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"
                >
                  <RefreshCw size={13} className={jobsLoading ? 'animate-spin' : ''} />
                </button>
              </div>
            </div>

            {(!jobsData || jobsData.jobs.length === 0) ? (
              <p className="text-sm text-gray-400 text-center py-4">
                {jobsData ? '暂无任务' : '加载中..'}
              </p>
            ) : (
              <div className="space-y-3">
                {jobsData.jobs.map(job => (
                  <div key={job.id} className="border rounded-xl p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900 text-sm">{job.name}</p>
                        <p className="text-xs text-gray-400 mt-0.5 font-mono truncate">{job.trigger_str}</p>
                      </div>
                      <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${
                        job.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {job.status === 'active' ? '活跃' : '暂停'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-gray-50 rounded-lg p-2">
                        <p className="text-gray-400 mb-0.5">下次运行</p>
                        <p className="font-medium text-gray-700">
                          {job.next_run_time
                            ? new Date(job.next_run_time).toLocaleString('zh-CN')
                            : <span className="text-yellow-600">已暂停</span>}
                        </p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-2">
                        <p className="text-gray-400 mb-0.5">任务 ID</p>
                        <p className="font-mono text-gray-600 truncate">{job.id}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => jobControlAction('run-now', job.id)}
                        disabled={!!jobAction}
                        className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Play size={11} />
                        {jobAction === `run-now:${job.id}` ? '执行中..' : '立即执行'}
                      </button>
                      {job.status === 'active' ? (
                        <button
                          onClick={() => jobControlAction('pause', job.id)}
                          disabled={!!jobAction}
                          className="px-3 py-1.5 bg-yellow-100 text-yellow-700 rounded-lg text-xs font-medium hover:bg-yellow-200 disabled:opacity-50"
                        >
                          {jobAction === `pause:${job.id}` ? '暂停中..' : '暂停'}
                        </button>
                      ) : (
                        <button
                          onClick={() => jobControlAction('resume', job.id)}
                          disabled={!!jobAction}
                          className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-medium hover:bg-green-200 disabled:opacity-50"
                        >
                          {jobAction === `resume:${job.id}` ? '恢复中..' : '恢复'}
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (editingJobId === job.id) {
                            setEditingJobId(null); setEditCron({});
                          } else {
                            setEditingJobId(job.id);
                            setEditCron({
                              day_of_week: job.cron_fields.day_of_week,
                              hour: Number(job.cron_fields.hour) || 0,
                              minute: Number(job.cron_fields.minute) || 0,
                            });
                          }
                        }}
                        className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200"
                      >
                        {editingJobId === job.id ? '取消' : '编辑时间'}
                      </button>
                    </div>

                    {editingJobId === job.id && (
                      <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 space-y-3">
                        <p className="text-xs font-semibold text-purple-800">修改执行时间</p>
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="text-xs text-purple-600 mb-1 block">星期</label>
                            <select
                              value={editCron.day_of_week ?? ''}
                              onChange={e => setEditCron(p => ({ ...p, day_of_week: e.target.value }))}
                              className="w-full border border-purple-300 rounded-lg px-2 py-1.5 text-sm bg-white"
                            >
                              <option value="*">每天</option>
                              <option value="mon">周一</option>
                              <option value="tue">周二</option>
                              <option value="wed">周三</option>
                              <option value="thu">周四</option>
                              <option value="fri">周五</option>
                              <option value="sat">周六</option>
                              <option value="sun">周日</option>
                            </select>
                          </div>
                          <div>
                            <label className="text-xs text-purple-600 mb-1 block">小时 (0-23)</label>
                            <input
                              type="number" min={0} max={23}
                              value={editCron.hour ?? 0}
                              onChange={e => setEditCron(p => ({ ...p, hour: Number(e.target.value) }))}
                              className="w-full border border-purple-300 rounded-lg px-2 py-1.5 text-sm bg-white"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-purple-600 mb-1 block">分钟 (0-59)</label>
                            <input
                              type="number" min={0} max={59}
                              value={editCron.minute ?? 0}
                              onChange={e => setEditCron(p => ({ ...p, minute: Number(e.target.value) }))}
                              className="w-full border border-purple-300 rounded-lg px-2 py-1.5 text-sm bg-white"
                            />
                          </div>
                        </div>
                        <button
                          onClick={() => saveJobCron(job.id)}
                          disabled={!!jobAction}
                          className="flex items-center gap-1 px-4 py-2 bg-purple-600 text-white rounded-lg text-xs font-medium hover:bg-purple-700 disabled:opacity-50"
                        >
                          {jobAction === `cron:${job.id}` ? '保存中..' : '保存'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

function FullCrawlBadge({ status }: { status: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    pending:   { cls: 'bg-gray-100 text-gray-600',    label: '待机' },
    running:   { cls: 'bg-blue-100 text-blue-700',    label: '进行中' },
    completed: { cls: 'bg-green-100 text-green-700',  label: '完成' },
    failed:    { cls: 'bg-red-100 text-red-700',      label: '失败' },
  };
  const { cls, label } = map[status] || map.pending;
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>{label}</span>;
}

function StatCard({ label, value, unit }: { label: string; value: string | number; unit: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-400">{unit}</p>
    </div>
  );
}

