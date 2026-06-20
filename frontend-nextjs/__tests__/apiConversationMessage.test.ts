const postMock = jest.fn();

jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: postMock,
    patch: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: {
        use: jest.fn(),
      },
    },
  })),
}));

describe('api.sendConversationMessage', () => {
  beforeEach(() => {
    jest.resetModules();
    postMock.mockReset();
    delete process.env.NEXT_PUBLIC_API_URL;
    postMock.mockResolvedValue({
      data: {
        session_id: 'session-1',
        reply: 'ok',
        intent: 'knowledge_qa',
        drafts_count: 0,
        upgrade_suggested: false,
        system_mode: 'conversation',
      },
    });
  });

  it('does not serialize the retired expert_perspective context field', async () => {
    const { api } = await import('@/lib/api');

    await (api.sendConversationMessage as any)(
      'session-1',
      '继续梳理任务书',
      undefined,
      { expert_perspective: '主矛盾视角' }
    );

    expect(postMock).toHaveBeenCalledWith('/api/v2/conversation/message', {
      session_id: 'session-1',
      message: '继续梳理任务书',
      in_response_to_card_id: undefined,
      selected_option_id: undefined,
      card_response: undefined,
    });
  });

  it('uses configured local backend directly instead of the Next.js proxy', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8001';

    await import('@/lib/api');

    const axios = await import('axios');
    expect(axios.default.create).toHaveBeenCalledWith(
      expect.objectContaining({
        baseURL: 'http://127.0.0.1:8001',
        timeout: 120000,
      }),
    );
  });
});
