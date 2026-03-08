/**
 * WorkflowRealtimeClient — 工作流实时通信客户端（单一入口）
 *
 * 合并自：
 *   - lib/websocket.ts (WebSocketClient)     — 心跳、重连、Safari 兼容
 *   - lib/reliable-ws.ts (ReliableWebSocket) — seq 去重、HTTP 事件回放（HISTORICAL）
 *
 * 架构说明：
 *   当前实现完整继承 WebSocketClient 能力。
 *   待后端 EventStore 支持 seq 字段后，可在此添加序号去重逻辑，
 *   无需修改 analysis/[sessionId]/page.tsx 的调用方式。
 *
 * 迁移指南：
 *   将 import { WebSocketClient } from '@/lib/websocket'
 *   替换为 import { WorkflowRealtimeClient } from '@/lib/workflow-realtime-client'
 *
 * 对应架构治理：P1 — WebSocket 客户端双实现合并
 * 创建时间：2026-03-04
 */

// 重新导出消息类型（保持调用方无需修改 type import）
export type {
  WebSocketMessage,
  MessageHandler,
  ErrorHandler,
  CloseHandler,
  WebSocketClientOptions as WorkflowRealtimeClientOptions,
} from './websocket';

import { WebSocketClient, type WebSocketClientOptions } from './websocket';

/**
 * WorkflowRealtimeClient — 工作流实时通信主类
 *
 * 功能：
 *  - 自动重连（指数退避，最大 30s）
 *  - 心跳检测（ping/pong，默认 30s 间隔）
 *  - 断线期间 isManualClose 标记，避免无效重连
 *  - Safari 浏览器增强重连机制
 *
 * Future (P2 / EventStore 就绪后)：
 *  - 断线补偿：通过 HTTP /api/analysis/events/{sessionId}?after_seq= 回放遗漏事件
 *  - seq 去重：丢弃重复序号消息
 */
export class WorkflowRealtimeClient extends WebSocketClient {
  constructor(options: WebSocketClientOptions) {
    super(options);
  }
}

/**
 * @deprecated 请使用 WorkflowRealtimeClient（从 @/lib/workflow-realtime-client 导入）
 * 此别名仅用于向后兼容，将在下一个主版本删除。
 */
export { WebSocketClient } from './websocket';
