/**
 * 🆕 P3优化: 用户友好错误提示映射
 * 
 * 将技术错误转换为用户可理解的提示
 */

export interface UserFriendlyError {
  title: string;
  message: string;
  action?: string;
  actionLabel?: string;
  severity: 'info' | 'warning' | 'error';
}

/**
 * 错误模式匹配配置
 */
const ERROR_PATTERNS: Array<{
  pattern: RegExp | string;
  mapping: UserFriendlyError;
}> = [
  // 网络相关
  {
    pattern: /network|timeout|fetch failed|ECONNREFUSED/i,
    mapping: {
      title: '网络连接失败',
      message: '无法连接到服务器，请检查网络连接',
      action: 'retry',
      actionLabel: '重试',
      severity: 'error'
    }
  },
  {
    pattern: /rate limit|429/i,
    mapping: {
      title: '请求过于频繁',
      message: '您的请求次数过多，请稍后再试',
      action: 'wait',
      actionLabel: '稍后重试',
      severity: 'warning'
    }
  },
  
  // 认证相关
  {
    pattern: /unauthorized|401|authentication/i,
    mapping: {
      title: '身份验证失败',
      message: 'API密钥无效或已过期，请检查配置',
      action: 'configure',
      actionLabel: '查看配置',
      severity: 'error'
    }
  },
  {
    pattern: /forbidden|403/i,
    mapping: {
      title: '访问被拒绝',
      message: '您没有权限执行此操作',
      severity: 'error'
    }
  },
  
  // 资源相关
  {
    pattern: /not found|404/i,
    mapping: {
      title: '资源未找到',
      message: '请求的内容不存在，可能已被删除',
      action: 'back',
      actionLabel: '返回',
      severity: 'warning'
    }
  },
  {
    pattern: /session.*not found|session.*expired/i,
    mapping: {
      title: '会话已过期',
      message: '您的会话已失效，请重新开始',
      action: 'restart',
      actionLabel: '重新开始',
      severity: 'warning'
    }
  },
  
  // 服务端错误
  {
    pattern: /500|internal server error|server error/i,
    mapping: {
      title: '服务器内部错误',
      message: '服务器遇到问题，我们正在处理',
      action: 'contact',
      actionLabel: '联系支持',
      severity: 'error'
    }
  },
  {
    pattern: /service unavailable|503/i,
    mapping: {
      title: '服务暂时不可用',
      message: '服务器正在维护或负载过高，请稍后再试',
      action: 'wait',
      actionLabel: '稍后重试',
      severity: 'warning'
    }
  },
  
  // 数据验证
  {
    pattern: /validation error|invalid input/i,
    mapping: {
      title: '输入内容有误',
      message: '请检查您输入的内容是否完整且符合要求',
      action: 'review',
      actionLabel: '查看详情',
      severity: 'warning'
    }
  },
  {
    pattern: /file too large|payload too large/i,
    mapping: {
      title: '文件过大',
      message: '上传的文件超过大小限制，请选择较小的文件',
      severity: 'warning'
    }
  },
  
  // WebSocket特定
  {
    pattern: /websocket.*closed|websocket.*failed/i,
    mapping: {
      title: '实时连接中断',
      message: '与服务器的实时连接已断开，正在尝试重连',
      action: 'retry',
      actionLabel: '手动重连',
      severity: 'warning'
    }
  },
  
  // LLM相关
  {
    pattern: /model.*unavailable|openai.*error/i,
    mapping: {
      title: 'AI服务暂时不可用',
      message: 'AI服务响应超时或不可用，请稍后再试',
      action: 'retry',
      actionLabel: '重试',
      severity: 'error'
    }
  },
  {
    pattern: /quota exceeded|insufficient_quota/i,
    mapping: {
      title: 'API配额已用尽',
      message: 'API调用次数已达上限，请检查您的配额',
      action: 'configure',
      actionLabel: '查看配置',
      severity: 'error'
    }
  },
  
  // PDF生成
  {
    pattern: /playwright.*not.*installed|browser.*not.*found/i,
    mapping: {
      title: 'PDF生成功能不可用',
      message: '服务器PDF生成组件未正确安装，请联系管理员',
      action: 'download_html',
      actionLabel: '下载HTML版本',
      severity: 'warning'
    }
  }
];

/**
 * 将技术错误转换为用户友好提示
 */
export function mapToUserFriendlyError(
  error: Error | string,
  context?: string
): UserFriendlyError {
  const errorMessage = typeof error === 'string' ? error : error.message;
  
  // 尝试匹配错误模式
  for (const { pattern, mapping } of ERROR_PATTERNS) {
    if (typeof pattern === 'string') {
      if (errorMessage.includes(pattern)) {
        return mapping;
      }
    } else {
      if (pattern.test(errorMessage)) {
        return mapping;
      }
    }
  }
  
  // 默认错误提示
  return {
    title: context || '操作失败',
    message: '抱歉，操作未能完成。如果问题持续出现，请联系技术支持。',
    action: 'retry',
    actionLabel: '重试',
    severity: 'error'
  };
}

/**
 * 获取HTTP状态码的友好提示
 */
export function getHttpErrorMessage(statusCode: number): UserFriendlyError {
  const statusMessages: Record<number, UserFriendlyError> = {
    400: {
      title: '请求错误',
      message: '请求格式不正确，请检查输入内容',
      severity: 'warning'
    },
    401: {
      title: '未授权',
      message: '请先登录或检查您的访问权限',
      action: 'login',
      actionLabel: '登录',
      severity: 'error'
    },
    403: {
      title: '访问被拒绝',
      message: '您没有权限访问此资源',
      severity: 'error'
    },
    404: {
      title: '资源不存在',
      message: '请求的内容未找到',
      action: 'back',
      actionLabel: '返回',
      severity: 'warning'
    },
    408: {
      title: '请求超时',
      message: '服务器响应超时，请重试',
      action: 'retry',
      actionLabel: '重试',
      severity: 'warning'
    },
    429: {
      title: '请求过多',
      message: '您的操作过于频繁，请稍后再试',
      action: 'wait',
      actionLabel: '稍后重试',
      severity: 'warning'
    },
    500: {
      title: '服务器错误',
      message: '服务器遇到问题，请稍后再试',
      action: 'contact',
      actionLabel: '联系支持',
      severity: 'error'
    },
    502: {
      title: '网关错误',
      message: '服务器暂时不可用，请稍后再试',
      action: 'retry',
      actionLabel: '重试',
      severity: 'error'
    },
    503: {
      title: '服务维护中',
      message: '服务正在维护，请稍后再试',
      action: 'wait',
      actionLabel: '稍后重试',
      severity: 'warning'
    },
    504: {
      title: '网关超时',
      message: '服务器响应超时，请重试',
      action: 'retry',
      actionLabel: '重试',
      severity: 'error'
    }
  };
  
  return statusMessages[statusCode] || {
    title: `错误 (${statusCode})`,
    message: '请求失败，请稍后重试',
    action: 'retry',
    actionLabel: '重试',
    severity: 'error'
  };
}

/**
 * 🆕 P3优化: 错误提示组件辅助函数
 */
export function formatErrorForDisplay(
  error: unknown,
  context?: string
): UserFriendlyError {
  if (error instanceof Error) {
    return mapToUserFriendlyError(error, context);
  }
  
  if (typeof error === 'string') {
    return mapToUserFriendlyError(error, context);
  }
  
  if (error && typeof error === 'object' && 'message' in error) {
    return mapToUserFriendlyError(String((error as any).message), context);
  }
  
  return {
    title: context || '未知错误',
    message: '发生了意外错误，请重试或联系技术支持',
    action: 'retry',
    actionLabel: '重试',
    severity: 'error'
  };
}
