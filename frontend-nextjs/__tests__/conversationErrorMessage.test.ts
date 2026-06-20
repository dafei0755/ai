import { buildConversationErrorMessage } from '@/lib/conversationErrorMessage';

describe('buildConversationErrorMessage', () => {
  it('surfaces the demand reconstruction LLM unavailable 503 detail', () => {
    const message = buildConversationErrorMessage({
      response: {
        status: 503,
        data: { detail: '智能识别暂不可用，请重试' },
      },
    });

    expect(message).toContain('智能识别暂不可用，请重试');
    expect(message).toContain('没有使用规则蓝图降级生成');
  });
});