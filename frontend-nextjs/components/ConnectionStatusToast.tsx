/**
 * 🆕 P3优化: WebSocket连接状态提示组件
 *
 * 提供用户友好的连接状态反馈
 */

import { useState, useEffect } from 'react';

export type ConnectionStatus = 'connected' | 'connecting' | 'reconnecting' | 'disconnected' | 'error';

interface ConnectionStatusToastProps {
  status: ConnectionStatus;
  reconnectAttempt?: number;
  maxAttempts?: number;
  nextRetrySeconds?: number;
  onManualRetry?: () => void;
}

export function ConnectionStatusToast({
  status,
  reconnectAttempt = 0,
  maxAttempts = 5,
  nextRetrySeconds = 0,
  onManualRetry
}: ConnectionStatusToastProps) {
  const [countdown, setCountdown] = useState(nextRetrySeconds);

  useEffect(() => {
    setCountdown(nextRetrySeconds);
  }, [nextRetrySeconds]);

  useEffect(() => {
    if (countdown > 0 && status === 'reconnecting') {
      const timer = setInterval(() => {
        setCountdown((prev) => Math.max(0, prev - 1));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [countdown, status]);

  // 不显示正常连接状态
  if (status === 'connected') {
    return null;
  }

  const statusConfig = {
    connecting: {
      icon: '🔌',
      color: 'bg-blue-50 border-blue-200 text-blue-800',
      title: '正在连接...',
      description: '建立实时连接中，请稍候'
    },
    reconnecting: {
      icon: '🔄',
      color: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      title: '连接中断',
      description: `正在尝试重连 (${reconnectAttempt}/${maxAttempts})${countdown > 0 ? `, ${countdown}秒后重试` : ''}`
    },
    disconnected: {
      icon: '⚠️',
      color: 'bg-orange-50 border-orange-200 text-orange-800',
      title: '连接已断开',
      description: '实时更新功能暂时不可用'
    },
    error: {
      icon: '❌',
      color: 'bg-red-50 border-red-200 text-red-800',
      title: '连接失败',
      description: reconnectAttempt >= maxAttempts
        ? '已达最大重试次数，请刷新页面或联系技术支持'
        : '网络连接出现问题'
    }
  };

  const config = statusConfig[status];

  return (
    <div
      className={`fixed top-4 right-4 z-50 max-w-sm rounded-lg border-2 p-4 shadow-lg animate-slide-in ${config.color}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl flex-shrink-0">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm mb-1">{config.title}</h3>
          <p className="text-xs opacity-90">{config.description}</p>

          {/* 重连按钮（仅在断开或错误状态显示） */}
          {(status === 'disconnected' || (status === 'error' && reconnectAttempt >= maxAttempts)) && onManualRetry && (
            <button
              onClick={onManualRetry}
              className="mt-2 text-xs font-medium underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-offset-1 rounded"
            >
              手动重连
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * 🆕 P3优化: useWebSocketStatus Hook
 *
 * 管理WebSocket连接状态和UI提示
 */
export function useWebSocketStatus() {
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [nextRetrySeconds, setNextRetrySeconds] = useState(0);

  const handleConnected = () => {
    setStatus('connected');
    setReconnectAttempt(0);
    setNextRetrySeconds(0);
  };

  const handleConnecting = () => {
    setStatus('connecting');
  };

  const handleReconnecting = (attempt: number, delaySeconds: number) => {
    setStatus('reconnecting');
    setReconnectAttempt(attempt);
    setNextRetrySeconds(delaySeconds);
  };

  const handleDisconnected = () => {
    setStatus('disconnected');
  };

  const handleError = () => {
    setStatus('error');
  };

  return {
    status,
    reconnectAttempt,
    nextRetrySeconds,
    handlers: {
      onConnected: handleConnected,
      onConnecting: handleConnecting,
      onReconnecting: handleReconnecting,
      onDisconnected: handleDisconnected,
      onError: handleError
    }
  };
}

// Tailwind动画配置（添加到globals.css）
/*
@keyframes slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.animate-slide-in {
  animation: slide-in 0.3s ease-out;
}
*/
