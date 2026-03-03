/**
 * WebSocket 客户端封装
 *
 * 提供自动重连、心跳检测、消息处理等功能
 */

export type WebSocketMessage =
  | { type: 'initial_status'; status: string; progress: number; current_node?: string; detail?: string }
  | { type: 'status_update'; status: string; progress?: number; current_node?: string; detail?: string; message?: string; error?: string; rejection_message?: string; final_report?: string }
  | { type: 'status'; status: string; progress?: number; message?: string; error?: string; final_report?: string }
  | { type: 'node_update'; current_node: string; node_name?: string; detail: string; timestamp: string }  // ✅ 统一使用 current_node，保留 node_name 用于向后兼容
  | { type: 'interrupt'; status: string; interrupt_data: any }
  | { type: 'followup_answer'; turn_id: number; question: string; answer: string; intent: string; referenced_sections: string[]; timestamp: string }  // 🔥 v3.11 新增：追问回答推送
  | { type: 'tool_permissions_initialized'; tool_settings: any }  // 🆕 v7.129: 工具权限初始化
  | { type: 'problem_solving_approach_ready'; data: any }  // 🆕 v7.270: 解题思路就绪
  | { type: 'step1_complete'; data: any }  // 🆕 v7.270: 第一步完成
  | { type: 'step2_start'; data: any }  // 🆕 v7.270: 第二步开始
  | { type: 'step2_complete'; data: any }  // 🆕 v7.270: 第二步完成
  | { type: 'batch_started'; batch_detail: any; timestamp: string }  // 🆕 v8.2: 批次开始
  | { type: 'batch_progress'; batch_detail: any; timestamp: string }  // 🆕 v8.2: 批次进度
  | { type: 'ping' }
  | { type: 'pong' };

export type MessageHandler = (message: WebSocketMessage) => void;
export type ErrorHandler = (error: Event) => void;
export type CloseHandler = () => void;

export interface WebSocketClientOptions {
  /** WebSocket 服务器 URL（不包含协议） */
  url: string;
  /** 会话 ID */
  sessionId: string;
  /** 消息处理函数 */
  onMessage: MessageHandler;
  /** 错误处理函数 */
  onError?: ErrorHandler;
  /** 连接关闭处理函数 */
  onClose?: CloseHandler;
  /** 连接成功处理函数（用于重连后状态同步） */
  onOpen?: () => void;
  /** 最大重连次数，默认 5 */
  maxReconnectAttempts?: number;
  /** 重连延迟（毫秒），默认 3000 */
  reconnectDelay?: number;
  /** 心跳间隔（毫秒），默认 30000 (30秒) */
  heartbeatInterval?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private sessionId: string;
  private onMessage: MessageHandler;
  private onError?: ErrorHandler;
  private onClose?: CloseHandler;
  private onOpen?: () => void;
  private maxReconnectAttempts: number;
  private reconnectDelay: number;
  private heartbeatInterval: number;
  private reconnectAttempts = 0;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;  // 🆕 P2修复: 重连定时器引用
  private isManualClose = false;
  private isSafari = false;  // 🆕 P2修复: Safari浏览器检测

  constructor(options: WebSocketClientOptions) {
    this.url = options.url;
    this.sessionId = options.sessionId;
    this.onMessage = options.onMessage;
    this.onError = options.onError;
    this.onClose = options.onClose;
    this.onOpen = options.onOpen;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 5;
    this.reconnectDelay = options.reconnectDelay ?? 3000;
    this.heartbeatInterval = options.heartbeatInterval ?? 30000;

    // 🆕 P2修复: Safari浏览器检测
    if (typeof window !== 'undefined' && typeof navigator !== 'undefined') {
      this.isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
      if (this.isSafari) {
        console.log('🍎 检测到Safari浏览器，启用增强重连机制');
      }
    }
  }

  /**
   * 连接 WebSocket
   */
  connect() {
    try {
      // 🆕 P2修复: 清理旧连接和定时器
      this.cleanup();

      // 构造 WebSocket URL (使用 ws:// 或 wss://)
      const protocol = this.url.startsWith('https') ? 'wss' : 'ws';
      const baseUrl = this.url.replace(/^https?:\/\//, '');
      const wsUrl = `${protocol}://${baseUrl}/ws/${this.sessionId}`;

      console.log(`🔌 连接 WebSocket: ${wsUrl}`);

      this.ws = new WebSocket(wsUrl);

      // 连接打开
      this.ws.onopen = () => {
        console.log('✅ WebSocket 连接成功');
        this.reconnectAttempts = 0; // 重置重连计数
        this.startHeartbeat(); // 启动心跳

        // 🔧 v7.118: 调用 onOpen 回调（用于重连后状态同步）
        this.onOpen?.();
      };

      // 接收消息
      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          // 处理 ping/pong
          if (message.type === 'ping') {
            this.send({ type: 'pong' });
            return;
          }

          // 调用消息处理函数
          this.onMessage(message);
        } catch (error) {
          console.error('❌ 解析 WebSocket 消息失败:', error);
        }
      };

      // 连接错误
      this.ws.onerror = (event) => {
        console.error('❌ WebSocket 错误:', event);
        this.onError?.(event);

        // 🆕 P2修复: Safari在onerror后不总是触发onclose，手动触发重连
        if (this.isSafari) {
          console.log('🍎 Safari错误处理：预调度重连');
          this.scheduleReconnect();
        }
      };

      // 连接关闭
      this.ws.onclose = (event) => {
        console.log(`🔌 WebSocket 连接关闭 (code: ${event.code}, reason: ${event.reason || 'unknown'})`);
        this.stopHeartbeat();
        this.onClose?.();

        // 🆕 P2修复: 使用专用重连方法
        this.scheduleReconnect();
      };

    } catch (error) {
      console.error('❌ 创建 WebSocket 连接失败:', error);
      this.scheduleReconnect();  // 🆕 P2修复: 创建失败也触发重连
    }
  }

  /**
   * 🆕 P2修复: 调度重连（避免重复定时器）
   */
  private scheduleReconnect() {
    // 如果是手动关闭，不重连
    if (this.isManualClose) {
      return;
    }

    // 如果已达到最大重连次数，停止
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ 达到最大重连次数，停止重连');
      return;
    }

    // 清除旧的重连定时器（避免重复）
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // 计算延迟（指数退避，Safari使用更长延迟）
    this.reconnectAttempts++;
    const baseDelay = this.isSafari ? this.reconnectDelay * 1.5 : this.reconnectDelay;
    const delay = Math.min(baseDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);

    console.log(`🔄 ${delay / 1000}秒后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})${this.isSafari ? ' [Safari增强模式]' : ''}...`);

    // 设置新的重连定时器
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  /**
   * 🆕 P2修复: 清理资源（防止内存泄漏）
   */
  private cleanup() {
    // 清理心跳定时器
    this.stopHeartbeat();

    // 清理重连定时器
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // 关闭旧连接（不触发回调）
    if (this.ws) {
      const oldWs = this.ws;
      oldWs.onopen = null;
      oldWs.onmessage = null;
      oldWs.onerror = null;
      oldWs.onclose = null;

      if (oldWs.readyState === WebSocket.OPEN || oldWs.readyState === WebSocket.CONNECTING) {
        oldWs.close();
      }

      this.ws = null;
    }
  }

  /**
   * 发送消息
   */
  private send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }

  /**
   * 启动心跳
   */
  private startHeartbeat() {
    this.stopHeartbeat(); // 先清除旧的定时器
    this.heartbeatTimer = setInterval(() => {
      this.send('ping');
    }, this.heartbeatInterval);
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 手动关闭连接
   */
  close() {
    this.isManualClose = true;
    this.cleanup();  // 🆕 P2修复: 使用统一的cleanup方法
  }

  /**
   * 获取连接状态
   */
  getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
