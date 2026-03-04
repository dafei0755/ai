/**
 * HISTORICAL — 未被任何页面导入的实验性实现
 *
 * 查明：本文件在 frontend-nextjs 中无任何调用方。
 * MT-4 设计目标（seq 去重、HTTP 事件回放）已识别为直实现的方向。
 * 待后端 EventStore 支持 seq 字段后，将将其逻辑并入 WorkflowRealtimeClient。
 *
 * 请勿新增调用方。待删除：2026-09-01
 *
 * 原功能（供参考）：
 *  - 自动重连（指数退避，最大 30s）
 *  - 断线期间追踪 lastSeq，重连后通过 HTTP API 补偿遗漏事件
 *  - 事件去重（seq 不回退）
 */

export interface WSEvent {
  seq: number;
  session_id: string;
  timestamp: number;
  payload: Record<string, unknown>;
}

export interface ReliableWSOptions {
  /** 初始重连延迟（ms），默认 1000 */
  initialReconnectDelay?: number;
  /** 最大重连延迟（ms），默认 30000 */
  maxReconnectDelay?: number;
  /** 每次退避倍率，默认 2 */
  backoffMultiplier?: number;
  /** 最大重连次数（0 = 无限），默认 0 */
  maxRetries?: number;
}

type EventCallback = (event: WSEvent) => void;
type StatusCallback = (status: 'connected' | 'disconnected' | 'reconnecting') => void;

const DEFAULT_OPTIONS: Required<ReliableWSOptions> = {
  initialReconnectDelay: 1000,
  maxReconnectDelay: 30_000,
  backoffMultiplier: 2,
  maxRetries: 0,
};

export class ReliableWebSocket {
  private ws: WebSocket | null = null;
  private lastSeq = 0;
  private retryCount = 0;
  private currentDelay: number;
  private closed = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly opts: Required<ReliableWSOptions>;

  constructor(
    /** WebSocket URL，例如 ws://... */
    private readonly wsUrl: string,
    /** 事件回放 HTTP API URL，例如 /api/analysis/events/{sessionId} */
    private readonly eventsApiUrl: string,
    /** 收到每条事件时的回调 */
    private readonly onEvent: EventCallback,
    /** 连接状态变更回调（可选） */
    private readonly onStatus?: StatusCallback,
    options?: ReliableWSOptions,
  ) {
    this.opts = { ...DEFAULT_OPTIONS, ...options };
    this.currentDelay = this.opts.initialReconnectDelay;
  }

  /** 建立连接（首次调用时使用）。 */
  connect(): void {
    this.closed = false;
    this._createSocket();
  }

  /** 主动关闭连接，不再重连。 */
  close(): void {
    this.closed = true;
    this._clearReconnectTimer();
    if (this.ws) {
      this.ws.close(1000, 'client close');
      this.ws = null;
    }
  }

  /** 当前已确认的最后一个事件序号。 */
  get currentSeq(): number {
    return this.lastSeq;
  }

  // ── 私有方法 ──────────────────────────────────────────────────────────────

  private _createSocket(): void {
    try {
      this.ws = new WebSocket(this.wsUrl);
    } catch (err) {
      console.error('[ReliableWS] WebSocket 创建失败:', err);
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      console.log('[ReliableWS] 已连接');
      this.retryCount = 0;
      this.currentDelay = this.opts.initialReconnectDelay;
      this.onStatus?.('connected');
      // 补偿断线期间遗漏的事件
      this._replayMissedEvents().catch((e) =>
        console.warn('[ReliableWS] 事件回放失败:', e),
      );
    };

    this.ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data as string) as Record<string, unknown>;
        // 如果消息带有 seq 字段（来自 EventStore），提取序号
        const seq = typeof data.seq === 'number' ? data.seq : 0;
        if (seq > 0 && seq <= this.lastSeq) {
          // 重复事件，丢弃
          return;
        }
        if (seq > this.lastSeq) {
          this.lastSeq = seq;
        }
        const event: WSEvent = {
          seq,
          session_id: (data.session_id as string) ?? '',
          timestamp: (data.timestamp as number) ?? Date.now() / 1000,
          payload: (data.payload as Record<string, unknown>) ?? data,
        };
        this.onEvent(event);
      } catch (e) {
        console.warn('[ReliableWS] 消息解析失败:', e);
      }
    };

    this.ws.onerror = (ev) => {
      console.warn('[ReliableWS] WebSocket 错误:', ev);
    };

    this.ws.onclose = (ev) => {
      console.log(`[ReliableWS] 连接关闭 code=${ev.code}`);
      this.ws = null;
      if (!this.closed) {
        this.onStatus?.('disconnected');
        this._scheduleReconnect();
      }
    };
  }

  private _scheduleReconnect(): void {
    if (this.closed) return;
    const { maxRetries } = this.opts;
    if (maxRetries > 0 && this.retryCount >= maxRetries) {
      console.warn('[ReliableWS] 已达最大重连次数，停止重连');
      return;
    }
    this.retryCount++;
    const delay = this.currentDelay;
    console.log(`[ReliableWS] ${delay}ms 后重连 (第 ${this.retryCount} 次)`);
    this.onStatus?.('reconnecting');
    this.reconnectTimer = setTimeout(() => {
      this.currentDelay = Math.min(
        this.currentDelay * this.opts.backoffMultiplier,
        this.opts.maxReconnectDelay,
      );
      this._createSocket();
    }, delay);
  }

  private _clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /** 通过 HTTP API 获取断线期间遗漏的事件，逐个回调。 */
  private async _replayMissedEvents(): Promise<void> {
    if (this.lastSeq === 0) return; // 首次连接，无需回放
    const url = `${this.eventsApiUrl}?after_seq=${this.lastSeq}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      console.warn(`[ReliableWS] 事件回放 HTTP 失败: ${resp.status}`);
      return;
    }
    const body = (await resp.json()) as { events: WSEvent[]; count: number };
    if (body.count === 0) return;
    console.log(`[ReliableWS] 补偿 ${body.count} 个遗漏事件`);
    for (const ev of body.events) {
      if (ev.seq > this.lastSeq) {
        this.lastSeq = ev.seq;
        this.onEvent(ev);
      }
    }
  }
}

export default ReliableWebSocket;
