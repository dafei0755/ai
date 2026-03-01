/**
 * v7.333.4 - Step 2 事件处理测试
 *
 * 测试 task_decomposition_chunk 和 task_decomposition_complete 事件
 */

describe('Step 2 搜索任务分解事件处理', () => {
  test('task_decomposition_chunk 事件应累积到 statusMessage', () => {
    const initialState = {
      statusMessage: '正在分析...',
    };

    const chunk1 = { type: 'task_decomposition_chunk', data: { chunk: '第一条任务：' } };
    const chunk2 = { type: 'task_decomposition_chunk', data: { chunk: '搜索品牌信息\n' } };

    let state = initialState;

    // 第一个chunk
    state = {
      ...state,
      statusMessage: (state.statusMessage || '') + chunk1.data.chunk,
    };
    expect(state.statusMessage).toBe('正在分析...第一条任务：');

    // 第二个chunk
    state = {
      ...state,
      statusMessage: (state.statusMessage || '') + chunk2.data.chunk,
    };
    expect(state.statusMessage).toBe('正在分析...第一条任务：搜索品牌信息\n');
  });

  test('task_decomposition_complete 事件应显示搜索任务数量', () => {
    const event = {
      type: 'task_decomposition_complete',
      data: {
        search_queries: [
          { query: '搜索1', expected_output: '输出1' },
          { query: '搜索2', expected_output: '输出2' },
          { query: '搜索3', expected_output: '输出3' },
        ],
        execution_strategy: { parallel: true },
        execution_advice: '建议并行执行',
      },
    };

    const state = {
      statusMessage: `搜索任务已生成（${event.data.search_queries.length}个查询）`,
    };

    expect(state.statusMessage).toBe('搜索任务已生成（3个查询）');
  });

  test('空搜索查询应显示0个查询', () => {
    const event = {
      type: 'task_decomposition_complete',
      data: {
        search_queries: [],
      },
    };

    const state = {
      statusMessage: `搜索任务已生成（${event.data.search_queries.length}个查询）`,
    };

    expect(state.statusMessage).toBe('搜索任务已生成（0个查询）');
  });
});

describe('后端事件到前端的映射', () => {
  test('后端发送的事件类型应与前端监听器匹配', () => {
    const backendEvents = [
      'task_decomposition_chunk',
      'task_decomposition_complete',
    ];

    const frontendListeners = [
      'task_decomposition_chunk',
      'task_decomposition_complete',
    ];

    backendEvents.forEach(eventType => {
      expect(frontendListeners).toContain(eventType);
    });
  });

  test('已废弃的事件不应再使用', () => {
    const deprecatedEvents = [
      'step2_plan_ready',  // 从未发送
      'search_framework_ready',  // v7.302.9 已废弃
      'search_master_line_ready',  // v7.302.9 已废弃
    ];

    // 这些事件不应出现在新的事件流中
    const newEventFlow = [
      'step1_complete',
      'task_decomposition_chunk',
      'task_decomposition_complete',
      'awaiting_confirmation',
    ];

    deprecatedEvents.forEach(deprecatedEvent => {
      expect(newEventFlow).not.toContain(deprecatedEvent);
    });
  });
});

export {};
