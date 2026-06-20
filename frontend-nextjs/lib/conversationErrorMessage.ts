type ApiLikeError = {
  message?: string;
  response?: {
    status?: number;
    data?: {
      detail?: unknown;
      message?: unknown;
    };
  };
};

const DEMAND_RECONSTRUCTION_LLM_UNAVAILABLE = '智能识别暂不可用，请重试';

function asText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

export function buildConversationErrorMessage(error: unknown): string {
  const apiError = error as ApiLikeError | null | undefined;
  const status = apiError?.response?.status;
  const detail = asText(apiError?.response?.data?.detail) || asText(apiError?.response?.data?.message);

  if (status === 503 && detail.includes(DEMAND_RECONSTRUCTION_LLM_UNAVAILABLE)) {
    return [
      DEMAND_RECONSTRUCTION_LLM_UNAVAILABLE,
      '',
      '没有使用规则蓝图降级生成。请稍后重试，或检查后端 LLM 供应商配置。',
    ].join('\n');
  }

  if (detail) {
    return detail;
  }

  if (status === 503) {
    return '服务暂时不可用，请稍后重试。';
  }

  return asText(apiError?.message) || '消息发送失败，请稍后重试。';
}