'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { RefreshCw, Play, Calendar, CheckCircle, AlertCircle, Clock, RotateCcw,
  Database, Globe, TrendingUp, Activity, FileText, AlertTriangle, Search, X, Square, Download, ChevronLeft, ChevronRight, ExternalLink, Image, CheckSquare, MinusSquare } from 'lucide-react';

// ── 质检清单类型 ────────────────────────────────────────────────────────────────
interface QualityItem {
  id: number;
  source: string;
  title: string;
  title_zh: string | null;
  title_en: string | null;
  url: string;
  primary_category: string;
  publish_date: string | null;
  crawled_at: string | null;
  quality_score: number | null;
  has_description: boolean;
  image_count: number;
  year: number | null;
  area_sqm: number | null;
}
interface QualityListResponse {
  items: QualityItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  source_counts: Record<string, number>;
  category_counts: Record<string, number>;
}

// ── 数据概览类型 ────────────────────────────────────────────────────────────────
interface CrawlerAlert {
  timestamp: string;
  source: string;
  category: string;
  consecutive_failures: number;
  last_error: string;
  total_failed: number;
  total_success: number;
}

interface CrawlError {
  ts: string;
  source: string;
  category: string;
  url: string;
  error_type: string;
  message: string;
  consecutive_failures: number;
}
interface ErrorDiagnosis {
  level: 'ok' | 'info' | 'medium' | 'high' | 'critical';
  text: string;
}
interface CrawlErrorsResponse {
  errors: CrawlError[];
  total: number;
  summary: { by_type: Record<string, number>; by_source: Record<string, number> };
  diagnosis: ErrorDiagnosis[];
}

interface SyncHistory {
  id: number; source: string; category?: string;
  started_at: string; completed_at?: string;
  status: 'running' | 'completed' | 'failed' | 'circuit_break';
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
  status: 'pending' | 'running' | 'completed' | 'failed' | 'circuit_break';
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
      // 核心建筑类型（≥ 1000 篇）
      '商业建筑', '休闲娱乐', '住宅建筑', '文化建筑', '公共空间', '教育建筑', '装置',
      // 重要空间类型（500–999 篇）
      '咖啡厅', '公园', '公共职能建筑', '交通建筑', '庭院', '绿色建筑', '体育建筑', '综合体',
      // 补充空间类型（200–499 篇）
      '塔楼', '酒吧', '工作室', '民宿', '广场', '工业建筑', '中国乡建', '高层建筑',
      '工业建筑改造', '宗教建筑', '园区', '水池', '屋顶花园', '医疗建筑', '社区中心',
      '滨海建筑', '区域规划',
      // 细分空间类型（96–222 篇）
      '甜品店', '热带建筑', '中庭', '城市更新', '摩天楼', '茶室', '书店',
      '与动物有关的项目', '楼梯', '步道', '游乐场', '艺术中心', '生态修复',
      '古建保护与开发', '灯光设计', '平台', '公厕', 'Spa',
    ],
    schedule: '每周二 02:00',
    enabled: true,
    categoryTotals: {
      '商业建筑': 6169, '休闲娱乐': 5666, '住宅建筑': 5482, '文化建筑': 3545,
      '公共空间': 2140, '教育建筑': 1681, '装置': 1383,
      '咖啡厅': 988, '公园': 936, '公共职能建筑': 755, '交通建筑': 604,
      '庭院': 577, '绿色建筑': 558, '体育建筑': 530, '综合体': 527,
      '塔楼': 485, '酒吧': 479, '工作室': 413, '民宿': 408, '广场': 403,
      '工业建筑': 398, '中国乡建': 395, '高层建筑': 389, '工业建筑改造': 368,
      '宗教建筑': 348, '园区': 318, '水池': 285, '屋顶花园': 272,
      '医疗建筑': 269, '社区中心': 265, '滨海建筑': 263, '区域规划': 263,
      '甜品店': 222, '热带建筑': 210, '中庭': 204, '城市更新': 203,
      '摩天楼': 186, '茶室': 182, '书店': 171, '与动物有关的项目': 165,
      '楼梯': 145, '步道': 144, '游乐场': 136, '艺术中心': 130,
      '生态修复': 118, '古建保护与开发': 111, '灯光设计': 108, '平台': 105,
      '公厕': 97, 'Spa': 96,
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
  const [activeTab, setActiveTab] = useState<'overview' | 'schedule' | 'quality'>('overview');

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
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [stopping, setStopping] = useState(false);
  const syncSafetyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── 调度Tab 实时进度日志（localStorage 持久化）─────────────────────────────────────
  const SCHED_LOGS_KEY = 'crawler_sched_logs';
  const [schedLogs, setSchedLogsRaw] = useState<LogEntry[]>(() => {
    try {
      const saved = typeof window !== 'undefined' ? localStorage.getItem(SCHED_LOGS_KEY) : null;
      if (!saved) return [];
      // 迁移旧日志：无 source 字段的旧日志视为系统消息，避免污染各源标签
      return (JSON.parse(saved) as LogEntry[]).map(log =>
        log.source ? log : { ...log, source: 'system' }
      );
    } catch { return []; }
  });
  const setSchedLogs = useCallback((updater: LogEntry[] | ((prev: LogEntry[]) => LogEntry[])) => {
    setSchedLogsRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      try { localStorage.setItem(SCHED_LOGS_KEY, JSON.stringify(next.slice(-200))); } catch { /* quota */ }
      return next;
    });
  }, []);
  const schedLogContainerRef = useRef<HTMLDivElement>(null);
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

  // ── 质检清单 状态 ──────────────────────────────────────────────────────────
  const [qualityData, setQualityData] = useState<QualityListResponse | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [qualitySource, setQualitySource] = useState<string>('');
  const [qualityCategory, setQualityCategory] = useState<string>('');
  const [qualityKeyword, setQualityKeyword] = useState<string>('');
  const [qualityPage, setQualityPage] = useState(1);
  const [qualitySort, setQualitySort] = useState<string>('crawled_at');
  const [qualityOrder, setQualityOrder] = useState<string>('desc');
  const [qualityExporting, setQualityExporting] = useState(false);
  const [selectedQualityIds, setSelectedQualityIds] = useState<Set<number>>(new Set());

  // ── 数据概览 状态 ──────────────────────────────────────────────────────────
  const [syncHistory, setSyncHistory] = useState<SyncHistory[]>([]);
  const [sourceStats, setSourceStats] = useState<SourceStats[]>([]);
  const [qualityIssues, setQualityIssues] = useState<QualityIssue[]>([]);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewLastRefresh, setOverviewLastRefresh] = useState<Date | null>(null);

  // ── 熔断告警 状态 ──────────────────────────────────────────────────────────
  const [crawlerAlerts, setCrawlerAlerts] = useState<CrawlerAlert[]>([]);

  // ── 错误诊断 状态 ──────────────────────────────────────────────────────────
  const [crawlErrors, setCrawlErrors] = useState<CrawlErrorsResponse | null>(null);
  const [errorTypeFilter, setErrorTypeFilter] = useState<string>('all');

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
    let destroyed = false;  // cleanup 后置 true，阻止 onclose 触发重连（防 React StrictMode 双连）

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
        addSchedLog('info', 'WebSocket 已连接，等待爬虫事件...', 'system');
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'initial_state') {
          const initial: Record<string, TaskProgress> = {};
          data.data.forEach((t: TaskProgress) => { initial[t.task_id] = t; });
          setTasks(initial);
          if (data.data.length > 0) {
            addSchedLog('info', `恢复 ${data.data.length} 个任务状态`, 'system');
          }
        } else if (data.type === 'progress') {
          setTasks(prev => ({ ...prev, [data.data.task_id]: data.data }));
          const t: TaskProgress = data.data;
          const msg = t.current_url
            ? `[${t.source ?? t.task_id}] ${t.current_url}`
            : `[${t.source ?? t.task_id}] ${t.completed}/${t.total} (${t.progress_percent.toFixed(1)}%) 批次${t.current_batch}/${t.total_batches}`;
          addSchedLog('info', msg, t.source ?? 'system');
        } else if (data.type === 'log') {
          addLog(data.data.level, data.data.message);
          // source 必须有值：爬虫日志用后端传来的 source，无来源的用 'system'
          addSchedLog(data.data.level, data.data.message, data.data.source ?? 'system');
        }
      };
      ws.onerror = () => {
        addLog('error', 'WebSocket连接错误');
        addSchedLog('error', 'WebSocket 连接出错', 'system');
      };
      ws.onclose = () => {
        setConnected(false);
        if (destroyed) return;  // 主动 cleanup 触发的关闭，不重连
        addLog('warning', 'WebSocket断开，5秒后重连');
        addSchedLog('warning', 'WebSocket 断开，5s 后重连...', 'system');
        reconnectRef.current = setTimeout(connect, 5000);
      };
      wsRef.current = ws;
    }
    connect();

    // 每 30 秒发一次 ping，防止服务端空闲超时断开连接
    const heartbeat = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 30_000);

    return () => {
      destroyed = true;
      clearInterval(heartbeat);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [addLog]);

  useEffect(() => {
    if (showSchedLogs && schedLogContainerRef.current) {
      schedLogContainerRef.current.scrollTop = schedLogContainerRef.current.scrollHeight;
    }
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
    setSyncing(null);  // 切换数据源时重置按钮状态
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSource]);

  // 当 is_running 变为 true 时，说明爬虫已正式启动，清除「启动中」过渡状态
  useEffect(() => {
    if (sourceStatus?.is_running && syncing === 'sync') {
      if (syncSafetyTimerRef.current) clearTimeout(syncSafetyTimerRef.current);
      setSyncing(null);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceStatus?.is_running]);

  // ── 立即同步（按checkpoint继续爬取）─────────────────────────────────────────
  async function triggerSync(source: string = selectedSource) {
    setSyncing('sync');
    setTriggerMsg(null);
    // 安全超时：15s 内 is_running 未变 true 则自动清除「启动中」状态
    if (syncSafetyTimerRef.current) clearTimeout(syncSafetyTimerRef.current);
    syncSafetyTimerRef.current = setTimeout(() => setSyncing(prev => prev === 'sync' ? null : prev), 15000);
    try {
      const res = await fetch(`${CRAWLER_API}/schedule/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'incremental', source }),
      });
      const data = await res.json();
      if (data.status !== 'triggered') {
        // 未成功触发（已在跑、被禁用等），立即清除并显示原因
        clearTimeout(syncSafetyTimerRef.current!);
        setSyncing(null);
        setTriggerMsg(data.message || data.status);
      }
      // 快速轮询，尽快感知 is_running 变化
      [2000, 4000, 7000, 12000, 20000].forEach(d =>
        setTimeout(() => { fetchSchedule(); fetchSourceStatus(source); if (activeTab === 'overview') fetchOverview(); }, d)
      );
    } catch (e) {
      clearTimeout(syncSafetyTimerRef.current!);
      setSyncing(null);
      setTriggerMsg(`错误: ${e}`);
    }
    // 注意：成功触发时不在 finally 里清除 syncing
    // 由 useEffect 监听 is_running 变化来清除 syncing
  }

  // ── 清空 checkpoint 并重新爬取 ──────────────────────────────────────────────
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
      // Step 2: 触发爬取（checkpoint 已清空 → 从第1页重新爬，等同于旧版"全量"）
      const trigRes = await fetch(`${CRAWLER_API}/schedule/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'incremental', source }),
      });
      const trigData = await trigRes.json();
      setTriggerMsg(`已清空 ${resetData.cleared} 个 checkpoint，将从第1页重新爬取 ${trigData.message ?? ''}`);
      [2000, 4000, 7000, 12000, 20000].forEach(d =>
        setTimeout(() => { fetchSchedule(); fetchSourceStatus(source); if (activeTab === 'overview') fetchOverview(); }, d)
      );
    } catch (e) {
      setTriggerMsg(`错误: ${e}`);
    } finally {
      setSyncing(null);
    }
  }

  // ── 强制停止爬取 ────────────────────────────────────────────────────────────
  async function forceStop() {
    setStopping(true);
    setTriggerMsg(null);
    try {
      const res = await fetch(`${CRAWLER_API}/schedule/force-stop`, { method: 'POST' });
      const data = await res.json();
      setTriggerMsg(data.message || '已发送停止信号');
      setTimeout(() => { fetchSchedule(); fetchSourceStatus(selectedSource); }, 1500);
    } catch (e) {
      setTriggerMsg(`停止失败: ${e}`);
    } finally {
      setStopping(false);
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
      // 获取熔断告警
      try {
        const alertRes = await fetch(`${CRAWLER_API}/schedule/alerts?limit=5`);
        if (alertRes.ok) setCrawlerAlerts((await alertRes.json()).alerts || []);
      } catch { /* 告警接口可选，不影响主流程 */ }
      // 获取错误诊断日志
      try {
        const errRes = await fetch(`${CRAWLER_API}/schedule/errors?limit=30&hours=24`);
        if (errRes.ok) setCrawlErrors(await errRes.json());
      } catch { /* 错误诊断接口可选 */ }
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

  // ── 质检清单 数据获取 ────────────────────────────────────────────────────────
  const fetchQualityList = useCallback(async (
    p?: number, src?: string, cat?: string, kw?: string, s?: string, o?: string
  ) => {
    setQualityLoading(true);
    try {
      const params = new URLSearchParams();
      const pg = p ?? qualityPage;
      const srcVal = src ?? qualitySource;
      const catVal = cat ?? qualityCategory;
      const kwVal = kw ?? qualityKeyword;
      const sortVal = s ?? qualitySort;
      const orderVal = o ?? qualityOrder;
      params.set('page', String(pg));
      params.set('page_size', '50');
      params.set('sort', sortVal);
      params.set('order', orderVal);
      if (srcVal) params.set('source', srcVal);
      if (catVal) params.set('category', catVal);
      if (kwVal) params.set('keyword', kwVal);
      const res = await fetch(`${CRAWLER_API}/quality-list?${params}`);
      if (res.ok) {
        const data: QualityListResponse = await res.json();
        setQualityData(data);
      }
    } catch (e) { console.error('获取质检清单失败:', e); }
    finally { setQualityLoading(false); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qualitySource, qualityCategory, qualityKeyword, qualitySort, qualityOrder, qualityPage]);

  useEffect(() => {
    if (activeTab === 'quality') fetchQualityList();
  }, [activeTab, fetchQualityList]);

  // ── 质检清单 勾选辅助 ──────────────────────────────────────────────────────
  const toggleSelectItem = useCallback((id: number) => {
    setSelectedQualityIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (!qualityData) return;
    const pageIds = qualityData.items.map(i => i.id);
    setSelectedQualityIds(prev => {
      const allSelected = pageIds.every(id => prev.has(id));
      const next = new Set(prev);
      if (allSelected) {
        pageIds.forEach(id => next.delete(id));
      } else {
        pageIds.forEach(id => next.add(id));
      }
      return next;
    });
  }, [qualityData]);

  const clearSelection = useCallback(() => setSelectedQualityIds(new Set()), []);

  const handleQualityExport = useCallback(async () => {
    setQualityExporting(true);
    try {
      const params = new URLSearchParams();
      if (qualitySource) params.set('source', qualitySource);
      if (qualityCategory) params.set('category', qualityCategory);
      if (qualityKeyword) params.set('keyword', qualityKeyword);
      // 勾选了具体项目时，通过 POST 带 ids；否则按筛选条件导出全部
      let res: Response;
      if (selectedQualityIds.size > 0) {
        res = await fetch(`${CRAWLER_API}/quality-list/export`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: Array.from(selectedQualityIds) }),
        });
      } else {
        res = await fetch(`${CRAWLER_API}/quality-list/export?${params}`);
      }
      if (res.ok) {
        const blob = await res.blob();
        const disposition = res.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : 'crawl_quality_export.txt';
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) { console.error('导出失败:', e); }
    finally { setQualityExporting(false); }
  }, [qualitySource, qualityCategory, qualityKeyword, selectedQualityIds]);

  const handleQualitySort = useCallback((col: string) => {
    const newOrder = qualitySort === col && qualityOrder === 'desc' ? 'asc' : 'desc';
    setQualitySort(col);
    setQualityOrder(newOrder);
    setQualityPage(1);
    fetchQualityList(1, undefined, undefined, undefined, col, newOrder);
  }, [qualitySort, qualityOrder, fetchQualityList]);

  const overviewFormatTime = (iso: string) => {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60) return `${diff}秒前`;
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    return `${Math.floor(diff / 86400)}天前`;
  };
  const overviewStatusColor = (s: string) => ({
    completed: 'bg-green-100 text-green-800', running: 'bg-blue-100 text-blue-800',
    failed: 'bg-red-100 text-red-800', circuit_break: 'bg-orange-100 text-orange-800',
    crashed: 'bg-gray-200 text-gray-700'
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
        {(['overview', 'schedule', 'quality'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'overview' ? '📊 数据概览' : tab === 'schedule' ? '⚙️ 调度计划' : '✅ 质检清单'}
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

          {/* 熔断告警 */}
          {crawlerAlerts.length > 0 && (
            <div className="bg-orange-50 border border-orange-300 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-orange-600" />
                <h2 className="font-bold text-orange-800 text-sm">🚨 熔断告警（{crawlerAlerts.length}）</h2>
              </div>
              <div className="space-y-2">
                {crawlerAlerts.map((a, i) => (
                  <div key={i} className="bg-white/80 rounded-lg px-4 py-3 border border-orange-200 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-gray-900">
                        {SOURCE_META[a.source]?.label ?? a.source} · {a.category}
                      </span>
                      <span className="text-gray-500 text-xs">{overviewFormatTime(a.timestamp)}</span>
                    </div>
                    <p className="text-gray-600">
                      连续失败 <span className="text-red-600 font-bold">{a.consecutive_failures}</span> 次后触发熔断
                      （成功 {a.total_success} / 失败 {a.total_failed}）
                    </p>
                    {a.last_error && (
                      <p className="text-red-600 text-xs mt-1 truncate" title={a.last_error}>
                        最后错误：{a.last_error}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

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
                    <React.Fragment key={s.id}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        {(() => {
                          const isStale = s.status === 'running' && s.started_at &&
                            (Date.now() - new Date(s.started_at).getTime()) > 30 * 60 * 1000;
                          const statusLabel = s.status === 'completed' ? '完成'
                            : s.status === 'crashed' ? '💀 已崩溃'
                            : s.status === 'running' ? (isStale ? '⚠️ 疑似卡死' : '运行中')
                            : s.status === 'circuit_break' ? '🚨 熔断' : '失败';
                          const colorClass = isStale ? 'bg-yellow-100 text-yellow-800' : overviewStatusColor(s.status);
                          return (
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${colorClass}`}
                              title={isStale ? `已运行 ${Math.round((Date.now() - new Date(s.started_at).getTime()) / 60000)} 分钟，可能已崩溃` : ''}>
                              {statusLabel}
                            </span>
                          );
                        })()}
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
                    {/* 熔断/崩溃时展开错误信息 */}
                    {(s.status === 'circuit_break' || s.status === 'crashed') && s.error_message && (
                      <tr className={s.status === 'crashed' ? 'bg-gray-50' : 'bg-orange-50'}>
                        <td colSpan={8} className={`px-4 py-2 text-xs ${s.status === 'crashed' ? 'text-gray-700' : 'text-orange-800'}`}>
                          {s.status === 'crashed' ? '💀' : '⚠️'} {s.error_message}
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  ))}
                  {syncHistory.length === 0 && (
                    <tr><td colSpan={8} className="px-4 py-10 text-center text-gray-400 text-sm">暂无同步记录</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 错误诊断面板 */}
          {crawlErrors && crawlErrors.total > 0 && (
            <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
              <div className="px-5 py-3 border-b flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Search className="w-4 h-4 text-red-500" />
                  <h2 className="font-semibold text-gray-900 text-sm">
                    错误自动诊断（最近24h · {crawlErrors.total} 个错误）
                  </h2>
                </div>
                <select
                  className="text-xs border rounded px-2 py-1 text-gray-600"
                  value={errorTypeFilter}
                  onChange={e => setErrorTypeFilter(e.target.value)}
                >
                  <option value="all">全部类型</option>
                  {Object.entries(crawlErrors.summary.by_type).map(([t, c]) => (
                    <option key={t} value={t}>
                      {({
                        parse_empty: '解析为空', validation_failed: '验证失败',
                        timeout: '超时', http_error: 'HTTP错误',
                        network_error: '网络错误', exception: '其他异常',
                      }[t] ?? t)} ({c})
                    </option>
                  ))}
                </select>
              </div>

              {/* 诊断建议 */}
              <div className="px-5 py-3 bg-gray-50 border-b space-y-1.5">
                {crawlErrors.diagnosis.map((d, i) => (
                  <div key={i} className={`flex items-start gap-2 text-sm ${
                    d.level === 'critical' ? 'text-red-700' :
                    d.level === 'high' ? 'text-orange-700' :
                    d.level === 'medium' ? 'text-yellow-700' :
                    d.level === 'ok' ? 'text-green-700' : 'text-gray-600'
                  }`}>
                    <span className="flex-shrink-0">{
                      d.level === 'critical' ? '🔴' :
                      d.level === 'high' ? '🟠' :
                      d.level === 'medium' ? '🟡' :
                      d.level === 'ok' ? '🟢' : 'ℹ️'
                    }</span>
                    <span>{d.text}</span>
                  </div>
                ))}
              </div>

              {/* 错误类型统计条 */}
              <div className="px-5 py-2 border-b flex items-center gap-3 flex-wrap">
                {Object.entries(crawlErrors.summary.by_type).map(([type, count]) => {
                  const labels: Record<string, string> = {
                    parse_empty: '解析为空', validation_failed: '验证失败',
                    timeout: '超时', http_error: 'HTTP错误',
                    network_error: '网络错误', exception: '其他异常',
                  };
                  const colors: Record<string, string> = {
                    parse_empty: 'bg-purple-100 text-purple-700',
                    validation_failed: 'bg-orange-100 text-orange-700',
                    timeout: 'bg-red-100 text-red-700',
                    http_error: 'bg-yellow-100 text-yellow-700',
                    network_error: 'bg-blue-100 text-blue-700',
                    exception: 'bg-gray-100 text-gray-700',
                  };
                  return (
                    <button
                      key={type}
                      onClick={() => setErrorTypeFilter(errorTypeFilter === type ? 'all' : type)}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold cursor-pointer transition-all ${
                        errorTypeFilter === type ? 'ring-2 ring-offset-1 ring-blue-400' : ''
                      } ${colors[type] ?? 'bg-gray-100 text-gray-700'}`}
                    >
                      {labels[type] ?? type}: {count}
                    </button>
                  );
                })}
              </div>

              {/* 错误明细表 */}
              <div className="overflow-x-auto max-h-80 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      {['时间', '类型', '数据源', '分类', 'URL', '错误信息'].map(h => (
                        <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {crawlErrors.errors
                      .filter(e => errorTypeFilter === 'all' || e.error_type === errorTypeFilter)
                      .map((e, i) => {
                        const typeLabels: Record<string, string> = {
                          parse_empty: '解析为空', validation_failed: '验证失败',
                          timeout: '超时', http_error: 'HTTP错误',
                          network_error: '网络错误', exception: '异常',
                        };
                        const typeColors: Record<string, string> = {
                          parse_empty: 'bg-purple-100 text-purple-700',
                          validation_failed: 'bg-orange-100 text-orange-700',
                          timeout: 'bg-red-100 text-red-700',
                          http_error: 'bg-yellow-100 text-yellow-700',
                          network_error: 'bg-blue-100 text-blue-700',
                          exception: 'bg-gray-100 text-gray-700',
                        };
                        return (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="px-3 py-2 text-gray-500 whitespace-nowrap text-xs">
                              {new Date(e.ts).toLocaleTimeString('zh-CN')}
                            </td>
                            <td className="px-3 py-2">
                              <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${typeColors[e.error_type] ?? 'bg-gray-100'}`}>
                                {typeLabels[e.error_type] ?? e.error_type}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-gray-900 text-xs capitalize">{e.source}</td>
                            <td className="px-3 py-2 text-gray-500 text-xs">{e.category}</td>
                            <td className="px-3 py-2 max-w-[200px]">
                              <a href={e.url} target="_blank" rel="noreferrer"
                                className="text-blue-600 hover:underline text-xs truncate block"
                                title={e.url}
                              >
                                {e.url.split('/').pop() || e.url}
                              </a>
                            </td>
                            <td className="px-3 py-2 text-gray-600 text-xs max-w-[300px]">
                              <span className="truncate block" title={e.message}>{e.message}</span>
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

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
              <div className="flex items-start gap-2">
                <span className="text-base leading-none mt-0.5">⚠️</span>
                <div>
                  <strong>定时调度器未运行</strong>，自动定时同步不可用。
                  <span className="ml-1 text-amber-700">「立即同步」按钮不受影响，可直接使用。</span>
                  <div className="mt-1.5 text-xs text-amber-600">
                    如需启用定时任务，请运行:
                    <code className="ml-1.5 bg-amber-100 px-2 py-0.5 rounded font-mono">python scripts/crawl_scheduler.py daemon</code>
                    <span className="ml-2 text-amber-500">（或通过 VS Code 任务：<em>🕷️ 启动爬虫调度器</em>）</span>
                  </div>
                </div>
              </div>
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
                <span>该数据源暂未实现，无法同步。如需启用，请修改 <code className="font-mono text-xs bg-amber-100 px-1 rounded">scripts/crawl_scheduler.py</code> 中的 <code className="font-mono text-xs bg-amber-100 px-1 rounded">enabled: True</code>，并完成对应 Spider 开发。</span>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              {(() => {
                const isRunning = sourceStatus?.is_running || Object.values(tasks).some(t => t.status === 'running');
                const isStarting = syncing === 'sync';
                const isDisabled = isRunning || isStarting || syncing !== null || sourceStatus?.enabled === false;
                return (
                  <>
                    <button
                      onClick={() => triggerSync(selectedSource)}
                      disabled={isDisabled}
                      className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all disabled:cursor-not-allowed ${
                        isRunning
                          ? 'bg-green-600 text-white opacity-80 cursor-default'
                          : isStarting
                          ? 'bg-blue-400 text-white opacity-80'
                          : 'bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50'
                      }`}
                    >
                      {isRunning
                        ? <><span className="w-2 h-2 rounded-full bg-white animate-pulse inline-block" /> 运行中...</>
                        : isStarting
                        ? <><RefreshCw size={14} className="animate-spin" /> 启动中...</>
                        : <><Play size={14} /> 立即同步</> }
                    </button>
                    {(isRunning || isStarting) && (
                      <button
                        onClick={forceStop}
                        disabled={stopping}
                        className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        title="发送停止信号，爬虫将在当前项目完成后退出"
                      >
                        {stopping
                          ? <><RefreshCw size={13} className="animate-spin" /> 停止中...</>
                          : <><Square size={13} fill="currentColor" /> 停止</> }
                      </button>
                    )}
                  </>
                );
              })()}
            </div>

            {/* 说明 */}
            <p className="text-xs text-gray-400 leading-relaxed">
              按 checkpoint 继续爬取，遇到已有 URL 时自动停止。首次同步将从第 1 页开始爬取全部历史数据。
            </p>

            {/* 高级操作（折叠） */}
            <div className="border-t border-gray-100 pt-3">
              <button
                onClick={() => setShowAdvanced(v => !v)}
                className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                <span className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`}>▶</span>
                高级操作
              </button>
              {showAdvanced && (
                <div className="mt-3 p-3 bg-orange-50 border border-orange-100 rounded-lg space-y-2">
                  <p className="text-xs text-orange-700 leading-relaxed">
                    <strong>清空并重新爬取</strong>：清除全部 checkpoint，强制从第 1 页重头爬取。
                    适用于：① Spider 分类列表变动后需刷新 ② 数据质量问题需全量重采。
                    <span className="text-orange-500 ml-1">普通同步无需执行此操作。</span>
                  </p>
                  <button
                    onClick={() => resetCheckpointAndSync(selectedSource)}
                    disabled={!!syncing || !!sourceStatus?.is_running || sourceStatus?.enabled === false}
                    className="flex items-center gap-2 px-3 py-1.5 bg-white text-orange-700 border border-orange-300 rounded-lg hover:bg-orange-100 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-medium"
                  >
                    {syncing === 'reset-sync'
                      ? <><RefreshCw size={12} className="animate-spin" /> 操作中...</>
                      : <><RotateCcw size={12} /> 清空并重新爬取</> }
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* ─── 实时进度 & 分类进度 左右布局 ─── */}
          <div className="flex gap-4 h-[calc(100vh-22rem)] min-h-[520px]">

          {/* 右列: 实时进度 / 日志 */}
          <div className="flex-1 min-w-0 order-2 h-full flex flex-col">
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
              <div className="bg-white border border-gray-200 shadow-sm flex flex-col h-full">
                {/* 面板标题栏 */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50 flex-shrink-0">
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
                    {(() => {
                      const srcCount = schedLogs.filter(l => l.source === selectedSource).length;
                      return srcCount > 0 ? (
                        <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded-full font-medium">
                          {srcCount} 条日志
                        </span>
                      ) : null;
                    })()}
                  </div>
                </div>

                {/* 内容滚动区 */}
                <div className="flex-1 min-h-0 overflow-y-auto">
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
                  <div ref={schedLogContainerRef} className="border-t border-gray-700 max-h-[480px] overflow-y-auto px-4 py-2 font-mono text-[12.5px] leading-6" style={{ backgroundColor: '#0d1117' }}>
                    {(() => {
                      // 过滤：严格隔离 —— 只显示当前数据源日志 + 系统消息（WS 连接/断开等）
                      const filtered = schedLogs.filter(log => log.source === selectedSource || log.source === 'system');
                      return filtered.length === 0 ? (
                        <p className="py-2 italic" style={{ color: '#8b949e' }}>等待日志...</p>
                      ) : filtered.map(log => {
                        const levelColor = log.level === 'error' ? '#ff6b6b' : log.level === 'warning' ? '#ffd93d' : '#6bcb77';
                        const msgColor   = log.level === 'error' ? '#ffb3b3' : log.level === 'warning' ? '#ffe08a' : '#e6edf3';
                        return (
                          <div key={log.id} className="flex items-start py-[3px]" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                            <span className="whitespace-nowrap flex-shrink-0 pr-2" style={{ color: '#79c0ff' }}>{log.timestamp}</span>
                            <span className="flex-shrink-0 px-1.5" style={{ color: '#484f58' }}>|</span>
                            <span className="w-12 flex-shrink-0 font-bold pr-2" style={{ color: levelColor }}>{log.level.slice(0,4).toUpperCase()}</span>
                            <span className="flex-shrink-0 px-1.5" style={{ color: '#484f58' }}>|</span>
                            <span className="break-all" style={{ color: msgColor }}>{log.message}</span>
                          </div>
                        );
                      });
                    })()
                    }
                    <div aria-hidden />
                  </div>
                )}
                </div>{/* 内容滚动区 end */}
              </div>
            );
          })()}
          </div>{/* 右列 end */}

          {/* 左列: 分类进度 */}
          <div className="w-[40%] flex-shrink-0 order-1 h-full flex flex-col">
          {/* ─── 分类进度列表 ─── */}
          <div className="bg-white shadow-sm border overflow-hidden flex flex-col flex-1">
            <div className="px-5 py-3 border-b bg-gray-50 flex items-center justify-between flex-shrink-0">
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

            <div className="flex-1 min-h-0 overflow-y-auto">
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
            </div>{/* 分类内容滚动区 end */}
          </div>
          </div>{/* 左列 end */}
          </div>{/* 左右布局 end */}

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

      {/* ═══ 质检清单 Tab ═══ */}
      {activeTab === 'quality' && (
        <div className="space-y-4">
          {/* 筛选栏 */}
          <div className="bg-white rounded-xl shadow-sm border p-4">
            <div className="flex flex-wrap items-end gap-3">
              {/* 数据源 */}
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 font-medium">数据源</label>
                <select
                  value={qualitySource}
                  onChange={e => { setQualitySource(e.target.value); setQualityCategory(''); setQualityPage(1); fetchQualityList(1, e.target.value, '', qualityKeyword); }}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white min-w-[140px]"
                >
                  <option value="">全部</option>
                  {Object.entries(qualityData?.source_counts || {}).map(([s, c]) => (
                    <option key={s} value={s}>{SOURCE_META[s]?.label || s} ({c})</option>
                  ))}
                </select>
              </div>
              {/* 分类 */}
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 font-medium">分类</label>
                <select
                  value={qualityCategory}
                  onChange={e => { setQualityCategory(e.target.value); setQualityPage(1); fetchQualityList(1, qualitySource, e.target.value, qualityKeyword); }}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white min-w-[140px]"
                >
                  <option value="">全部分类</option>
                  {Object.entries(qualityData?.category_counts || {}).sort((a, b) => b[1] - a[1]).map(([c, n]) => (
                    <option key={c} value={c}>{c} ({n})</option>
                  ))}
                </select>
              </div>
              {/* 关键词 */}
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 font-medium">标题搜索</label>
                <div className="relative">
                  <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    value={qualityKeyword}
                    onChange={e => setQualityKeyword(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { setQualityPage(1); fetchQualityList(1, qualitySource, qualityCategory, qualityKeyword); }}}
                    placeholder="输入关键词按回车搜索"
                    className="border border-gray-300 rounded-lg pl-8 pr-8 py-2 text-sm min-w-[200px]"
                  />
                  {qualityKeyword && (
                    <button onClick={() => { setQualityKeyword(''); setQualityPage(1); fetchQualityList(1, qualitySource, qualityCategory, ''); }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"><X size={14} /></button>
                  )}
                </div>
              </div>
              {/* 刷新 */}
              <button
                onClick={() => fetchQualityList()}
                disabled={qualityLoading}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                <RefreshCw size={14} className={qualityLoading ? 'animate-spin' : ''} />
                刷新
              </button>
              {/* 导出 */}
              <button
                onClick={handleQualityExport}
                disabled={qualityExporting}
                className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
              >
                <Download size={14} />
                {qualityExporting ? '导出中...' : selectedQualityIds.size > 0 ? `导出选中 (${selectedQualityIds.size})` : '导出 TXT'}
              </button>
              {/* 清除选择 */}
              {selectedQualityIds.size > 0 && (
                <button
                  onClick={clearSelection}
                  className="flex items-center gap-1.5 px-3 py-2 bg-gray-100 text-gray-600 rounded-lg text-sm hover:bg-gray-200"
                >
                  <X size={14} />
                  清除选择
                </button>
              )}
            </div>
            {/* 统计 */}
            {qualityData && (
              <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
                <span>共 <strong className="text-gray-900">{qualityData.total}</strong> 条记录</span>
                <span>第 {qualityData.page} / {qualityData.total_pages} 页</span>
                {selectedQualityIds.size > 0 && (
                  <span className="text-blue-600 font-medium">已选中 {selectedQualityIds.size} 项</span>
                )}
              </div>
            )}
          </div>

          {/* 清单表格 */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b">
                    <th className="text-center px-3 py-3 w-10">
                      <button onClick={toggleSelectAll} className="text-gray-500 hover:text-blue-600" title="全选/取消全选">
                        {qualityData && qualityData.items.length > 0 && qualityData.items.every(i => selectedQualityIds.has(i.id))
                          ? <CheckSquare size={16} className="text-blue-600" />
                          : qualityData && qualityData.items.some(i => selectedQualityIds.has(i.id))
                            ? <MinusSquare size={16} className="text-blue-400" />
                            : <Square size={16} />}
                      </button>
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 w-12">#</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-blue-600 select-none"
                      onClick={() => handleQualitySort('crawled_at')}>
                      <span className="flex items-center gap-1">
                        爬取日期
                        {qualitySort === 'crawled_at' && <span>{qualityOrder === 'desc' ? '↓' : '↑'}</span>}
                      </span>
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-blue-600 select-none"
                      onClick={() => handleQualitySort('source')}>
                      <span className="flex items-center gap-1">
                        数据源
                        {qualitySort === 'source' && <span>{qualityOrder === 'desc' ? '↓' : '↑'}</span>}
                      </span>
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">分类</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-blue-600 select-none"
                      onClick={() => handleQualitySort('title')}>
                      <span className="flex items-center gap-1">
                        标题
                        {qualitySort === 'title' && <span>{qualityOrder === 'desc' ? '↓' : '↑'}</span>}
                      </span>
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-blue-600 select-none"
                      onClick={() => handleQualitySort('publish_date')}>
                      <span className="flex items-center gap-1">
                        发布日期
                        {qualitySort === 'publish_date' && <span>{qualityOrder === 'desc' ? '↓' : '↑'}</span>}
                      </span>
                    </th>
                    <th className="text-center px-4 py-3 font-medium text-gray-600">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {qualityLoading && !qualityData && (
                    <tr><td colSpan={8} className="text-center py-12 text-gray-400">
                      <RefreshCw className="animate-spin inline mr-2" size={16} />加载中...
                    </td></tr>
                  )}
                  {qualityData && qualityData.items.length === 0 && (
                    <tr><td colSpan={8} className="text-center py-12 text-gray-400">暂无数据</td></tr>
                  )}
                  {qualityData?.items.map((item, idx) => (
                    <tr key={item.id} className={`hover:bg-blue-50/30 transition-colors ${selectedQualityIds.has(item.id) ? 'bg-blue-50/50' : ''}`}>
                      <td className="text-center px-3 py-3">
                        <button onClick={() => toggleSelectItem(item.id)} className="text-gray-400 hover:text-blue-600">
                          {selectedQualityIds.has(item.id)
                            ? <CheckSquare size={15} className="text-blue-600" />
                            : <Square size={15} />}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {(qualityData.page - 1) * qualityData.page_size + idx + 1}
                      </td>
                      <td className="px-4 py-3 text-gray-600 whitespace-nowrap text-xs">
                        {item.crawled_at || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          item.source === 'archdaily_cn' ? 'bg-blue-100 text-blue-700' :
                          item.source === 'gooood' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>{SOURCE_META[item.source]?.label || item.source}</span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{item.primary_category || '-'}</td>
                      <td className="px-4 py-3 max-w-[400px]">
                        <div className="flex items-start gap-1.5">
                          <a href={item.url} target="_blank" rel="noopener noreferrer"
                            className="text-gray-900 hover:text-blue-600 text-sm leading-snug line-clamp-2 break-all"
                            title={item.url}>
                            {item.title}
                          </a>
                          <ExternalLink size={12} className="text-gray-300 mt-0.5 flex-shrink-0" />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {item.publish_date || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1.5">
                          {item.has_description ? (
                            <span title="有描述" className="text-green-500"><CheckCircle size={14} /></span>
                          ) : (
                            <span title="缺少描述" className="text-orange-400"><AlertCircle size={14} /></span>
                          )}
                          {item.image_count > 0 ? (
                            <span title={`${item.image_count} 张图片`} className="text-blue-500 text-xs flex items-center gap-0.5">
                              <Image size={12} />{item.image_count}
                            </span>
                          ) : (
                            <span title="无图片" className="text-gray-300"><Image size={12} /></span>
                          )}
                          {item.quality_score !== null && (
                            <span title={`质量评分: ${item.quality_score}`}
                              className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                                item.quality_score >= 0.7 ? 'bg-green-100 text-green-700' :
                                item.quality_score >= 0.4 ? 'bg-yellow-100 text-yellow-700' :
                                'bg-red-100 text-red-700'
                              }`}>{item.quality_score}</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 分页 */}
          {qualityData && qualityData.total_pages > 1 && (
            <div className="flex items-center justify-between bg-white rounded-xl shadow-sm border px-4 py-3">
              <div className="text-sm text-gray-500">
                显示 {(qualityData.page - 1) * qualityData.page_size + 1}-{Math.min(qualityData.page * qualityData.page_size, qualityData.total)} / {qualityData.total}
              </div>
              <div className="flex items-center gap-2">
                <button
                  disabled={qualityData.page <= 1}
                  onClick={() => { const p = qualityData.page - 1; setQualityPage(p); fetchQualityList(p); }}
                  className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronLeft size={16} />
                </button>
                {/* 页码按钮 */}
                {Array.from({ length: Math.min(7, qualityData.total_pages) }, (_, i) => {
                  let pageNum: number;
                  if (qualityData.total_pages <= 7) {
                    pageNum = i + 1;
                  } else if (qualityData.page <= 4) {
                    pageNum = i + 1;
                  } else if (qualityData.page >= qualityData.total_pages - 3) {
                    pageNum = qualityData.total_pages - 6 + i;
                  } else {
                    pageNum = qualityData.page - 3 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => { setQualityPage(pageNum); fetchQualityList(pageNum); }}
                      className={`px-3 py-1 rounded-lg text-sm ${
                        pageNum === qualityData.page ? 'bg-blue-600 text-white' : 'hover:bg-gray-100 text-gray-600'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  disabled={qualityData.page >= qualityData.total_pages}
                  onClick={() => { const p = qualityData.page + 1; setQualityPage(p); fetchQualityList(p); }}
                  className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
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
