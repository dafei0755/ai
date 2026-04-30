'use client';

import { useEffect, useState } from 'react';

/**
 * WebSocket 连接测试页面
 * 用于诊断 WebSocket 连接问题
 */
export default function TestWebSocket() {
  const [logs, setLogs] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState('test-session-001');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, `[${timestamp}] ${message}`]);
  };

  const connectWebSocket = () => {
    try {
      const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
      addLog(`🔌 尝试连接: ${wsUrl}`);
      
      const websocket = new WebSocket(wsUrl);

      websocket.onopen = () => {
        addLog('✅ WebSocket 连接成功！');
        setConnected(true);
      };

      websocket.onmessage = (event) => {
        addLog(`📨 收到消息: ${event.data}`);
      };

      websocket.onerror = (event) => {
        addLog(`❌ WebSocket 错误: ${JSON.stringify(event)}`);
      };

      websocket.onclose = () => {
        addLog('🔌 WebSocket 连接关闭');
        setConnected(false);
      };

      setWs(websocket);
    } catch (error) {
      addLog(`❌ 连接失败: ${error}`);
    }
  };

  const disconnect = () => {
    if (ws) {
      ws.close();
      setWs(null);
    }
  };

  const sendPing = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send('ping');
      addLog('📤 发送: ping');
    } else {
      addLog('❌ WebSocket 未连接');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">WebSocket 连接测试</h1>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Session ID</label>
            <input
              type="text"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              disabled={connected}
            />
          </div>

          <div className="flex gap-4">
            <button
              onClick={connectWebSocket}
              disabled={connected}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-300"
            >
              连接
            </button>
            <button
              onClick={disconnect}
              disabled={!connected}
              className="px-4 py-2 bg-red-600 text-white rounded-lg disabled:bg-gray-300"
            >
              断开
            </button>
            <button
              onClick={sendPing}
              disabled={!connected}
              className="px-4 py-2 bg-green-600 text-white rounded-lg disabled:bg-gray-300"
            >
              发送 Ping
            </button>
          </div>

          <div className="mt-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-gray-300'}`}></div>
              <span className="text-sm">{connected ? '已连接' : '未连接'}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">日志输出</h2>
          <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm h-96 overflow-y-auto">
            {logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </div>
          <button
            onClick={() => setLogs([])}
            className="mt-4 px-4 py-2 bg-gray-600 text-white rounded-lg"
          >
            清空日志
          </button>
        </div>
      </div>
    </div>
  );
}
