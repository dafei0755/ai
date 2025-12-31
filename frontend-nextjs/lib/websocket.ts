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
  private maxReconnectAttempts: number;
  private reconnectDelay: number;
  private heartbeatInterval: number;
  private reconnectAttempts = 0;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private isManualClose = false;

  constructor(options: WebSocketClientOptions) {
    this.url = options.url;
    this.sessionId = options.sessionId;
    this.onMessage = options.onMessage;
    this.onError = options.onError;
    this.onClose = options.onClose;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 5;
    this.reconnectDelay = options.reconnectDelay ?? 3000;
    this.heartbeatInterval = options.heartbeatInterval ?? 30000;
  }

  /**
   * 连接 WebSocket
   */
  connect() {
    try {
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
      };

      // 连接关闭
      this.ws.onclose = () => {
        console.log('🔌 WebSocket 连接关闭');
        this.stopHeartbeat();
        this.onClose?.();

        // 如果不是手动关闭，尝试重连
        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`🔄 ${this.reconnectDelay / 1000}秒后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
          setTimeout(() => this.connect(), this.reconnectDelay);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error('❌ 达到最大重连次数，停止重连');
        }
      };

    } catch (error) {
      console.error('❌ 创建 WebSocket 连接失败:', error);
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
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
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
