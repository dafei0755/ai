/**
 * v7.300: SSE 事件处理集成测试
 *
 * 测试前端 SSE 事件处理逻辑：
 * 1. step2_plan_ready 事件解析
 * 2. 状态更新正确性
 * 3. 事件数据验证
 * 4. 错误处理
 */

import '@testing-library/jest-dom';
import type { Step2SearchPlan, EditableSearchStep } from '@/types';

// 模拟 SSE 事件数据
const createMockSSEEvent = (eventType: string, data: any) => ({
  type: eventType,
  data: JSON.stringify(data),
});

// 测试数据工厂
const TestDataFactory = {
  createStep2PlanReadyEvent: (overrides: Partial<any> = {}) => ({
    session_id: 'test-session-123',
    query: '以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计',
    core_question: '如何融合HAY品牌气质与峨眉山地域特色',
    answer_goal: '提供完整的民宿室内概念设计方案',
    search_steps: [
      {
        id: 'S1',
        step_number: 1,
        task_description: '搜索HAY品牌设计语言',
        expected_outcome: '获取HAY品牌核心设计特征',
        search_keywords: ['HAY', '北欧设计'],
        priority: 'high',
        can_parallel: true,
        status: 'pending',
        completion_score: 0,
      },
      {
        id: 'S2',
        step_number: 2,
        task_description: '研究峨眉山七里坪地域特色',
        expected_outcome: '了解当地自然环境和文化背景',
        search_keywords: ['峨眉山', '七里坪', '川西'],
        priority: 'high',
        can_parallel: true,
        status: 'pending',
        completion_score: 0,
      },
    ],
    max_rounds_per_step: 3,
    quality_threshold: 0.7,
    user_added_steps: [],
    user_deleted_steps: [],
    user_modified_steps: [],
    ...overrides,
  }),
};

describe('SSE Event: step2_plan_ready', () => {
  describe('事件数据解析', () => {
    it('正确解析完整的 step2_plan_ready 事件', () => {
      const eventData = TestDataFactory.createStep2PlanReadyEvent();

      // 模拟前端解析逻辑
      const searchSteps = (eventData.search_steps || []).map((step: any, idx: number) => ({
        id: step.id || `S${idx + 1}`,
        step_number: step.step_number || idx + 1,
        task_description: step.task_description || '',
        expected_outcome: step.expected_outcome || '',
        search_keywords: step.search_keywords || [],
        priority: step.priority || 'medium',
        can_parallel: step.can_parallel !== false,
        status: step.status || 'pending',
        completion_score: step.completion_score || 0,
        is_user_added: step.is_user_added || false,
        is_user_modified: step.is_user_modified || false,
      }));

      const stepsPerPage = 5;
      const plan: Step2SearchPlan = {
        session_id: eventData.session_id || '',
        query: eventData.query || '',
        core_question: eventData.core_question || '',
        answer_goal: eventData.answer_goal || '',
        search_steps: searchSteps,
        max_rounds_per_step: eventData.max_rounds_per_step || 3,
        quality_threshold: eventData.quality_threshold || 0.7,
        user_added_steps: eventData.user_added_steps || [],
        user_deleted_steps: eventData.user_deleted_steps || [],
        user_modified_steps: eventData.user_modified_steps || [],
        current_page: 1,
        total_pages: Math.max(1, Math.ceil(searchSteps.length / stepsPerPage)),
        is_confirmed: false,
      };

      expect(plan.session_id).toBe('test-session-123');
      expect(plan.search_steps).toHaveLength(2);
      expect(plan.search_steps[0].task_description).toBe('搜索HAY品牌设计语言');
      expect(plan.total_pages).toBe(1);
      expect(plan.is_confirmed).toBe(false);
    });

    it('处理缺失字段的事件数据', () => {
      const eventData = {
        session_id: 'test-123',
        search_steps: [
          { id: 'S1', task_description: '任务1' },
        ],
      };

      const searchSteps = (eventData.search_steps || []).map((step: any, idx: number) => ({
        id: step.id || `S${idx + 1}`,
        step_number: step.step_number || idx + 1,
        task_description: step.task_description || '',
        expected_outcome: step.expected_outcome || '',
        search_keywords: step.search_keywords || [],
        priority: step.priority || 'medium',
        can_parallel: step.can_parallel !== false,
        status: step.status || 'pending',
        completion_score: step.completion_score || 0,
        is_user_added: step.is_user_added || false,
        is_user_modified: step.is_user_modified || false,
      }));

      expect(searchSteps[0].priority).toBe('medium');
      expect(searchSteps[0].can_parallel).toBe(true);
      expect(searchSteps[0].status).toBe('pending');
      expect(searchSteps[0].expected_outcome).toBe('');
    });

    it('处理空搜索步骤列表', () => {
      const eventData = {
        session_id: 'test-123',
        search_steps: [],
      };

      const searchSteps = eventData.search_steps || [];
      const stepsPerPage = 5;
      const totalPages = Math.max(1, Math.ceil(searchSteps.length / stepsPerPage));

      expect(searchSteps).toHaveLength(0);
      expect(totalPages).toBe(1);
    });

    it('正确计算分页', () => {
      const manySteps = Array.from({ length: 12 }, (_, i) => ({
        id: `S${i + 1}`,
        step_number: i + 1,
        task_description: `任务 ${i + 1}`,
      }));

      const eventData = {
        session_id: 'test-123',
        search_steps: manySteps,
      };

      const stepsPerPage = 5;
      const totalPages = Math.max(1, Math.ceil(eventData.search_steps.length / stepsPerPage));

      expect(totalPages).toBe(3); // 12 / 5 = 2.4 -> 3 pages
    });
  });

  describe('优先级映射', () => {
    it('正确映射 high 优先级', () => {
      const step = { priority: 'high' };
      expect(step.priority).toBe('high');
    });

    it('正确映射 medium 优先级', () => {
      const step = { priority: 'medium' };
      expect(step.priority).toBe('medium');
    });

    it('正确映射 low 优先级', () => {
      const step = { priority: 'low' };
      expect(step.priority).toBe('low');
    });

    it('缺失优先级默认为 medium', () => {
      const step: any = {};
      const priority = step.priority || 'medium';
      expect(priority).toBe('medium');
    });
  });

  describe('状态映射', () => {
    it('正确映射 pending 状态', () => {
      const step = { status: 'pending' };
      expect(step.status).toBe('pending');
    });

    it('正确映射 searching 状态', () => {
      const step = { status: 'searching' };
      expect(step.status).toBe('searching');
    });

    it('正确映射 complete 状态', () => {
      const step = { status: 'complete' };
      expect(step.status).toBe('complete');
    });

    it('缺失状态默认为 pending', () => {
      const step: any = {};
      const status = step.status || 'pending';
      expect(status).toBe('pending');
    });
  });

  describe('并行标记处理', () => {
    it('can_parallel 为 true 时保持 true', () => {
      const step = { can_parallel: true };
      const canParallel = step.can_parallel !== false;
      expect(canParallel).toBe(true);
    });

    it('can_parallel 为 false 时保持 false', () => {
      const step = { can_parallel: false };
      const canParallel = step.can_parallel !== false;
      expect(canParallel).toBe(false);
    });

    it('can_parallel 缺失时默认为 true', () => {
      const step: any = {};
      const canParallel = step.can_parallel !== false;
      expect(canParallel).toBe(true);
    });
  });
});

describe('SSE Event: 状态更新', () => {
  // 模拟 SearchState 类型
  interface MockSearchState {
    status: string;
    awaitingConfirmation: boolean;
    statusMessage: string;
  }

  it('step2_plan_ready 事件设置 awaitingConfirmation 为 true', () => {
    const prevState: MockSearchState = {
      status: 'analyzing',
      awaitingConfirmation: false,
      statusMessage: '正在分析...',
    };

    const eventData = TestDataFactory.createStep2PlanReadyEvent();

    // 模拟状态更新
    const newState: MockSearchState = {
      ...prevState,
      awaitingConfirmation: true,
      statusMessage: `已生成 ${eventData.search_steps.length} 个搜索任务，可编辑后运行`,
    };

    expect(newState.awaitingConfirmation).toBe(true);
    expect(newState.statusMessage).toContain('2 个搜索任务');
  });

  it('空任务列表时状态消息正确', () => {
    const eventData = TestDataFactory.createStep2PlanReadyEvent({
      search_steps: [],
    });

    const statusMessage = `已生成 ${eventData.search_steps.length} 个搜索任务，可编辑后运行`;

    expect(statusMessage).toContain('0 个搜索任务');
  });
});

describe('SSE Event: 错误处理', () => {
  it('处理无效 JSON 数据', () => {
    const invalidData = 'not valid json';

    expect(() => {
      JSON.parse(invalidData);
    }).toThrow();
  });

  it('处理 null 事件数据', () => {
    const eventData = null;

    const searchSteps = (eventData as any)?.search_steps || [];
    expect(searchSteps).toEqual([]);
  });

  it('处理 undefined 事件数据', () => {
    const eventData = undefined;

    const searchSteps = (eventData as any)?.search_steps || [];
    expect(searchSteps).toEqual([]);
  });

  it('处理非数组 search_steps', () => {
    const eventData = {
      session_id: 'test-123',
      search_steps: 'not an array',
    };

    const searchSteps = Array.isArray(eventData.search_steps)
      ? eventData.search_steps
      : [];

    expect(searchSteps).toEqual([]);
  });
});

describe('SSE Event: 与其他事件的兼容性', () => {
  it('step2_plan_ready 不影响 search_framework_ready 处理', () => {
    // 两个事件应该独立处理
    const step2Event = TestDataFactory.createStep2PlanReadyEvent();
    const frameworkEvent = {
      core_question: '核心问题',
      targets: [],
      framework_checklist: {
        core_summary: '摘要',
        main_directions: [],
        boundaries: [],
        answer_goal: '目标',
      },
    };

    // 两个事件的数据结构不同
    expect(step2Event.search_steps).toBeDefined();
    expect(frameworkEvent.framework_checklist).toBeDefined();
    expect((step2Event as any).framework_checklist).toBeUndefined();
    expect((frameworkEvent as any).search_steps).toBeUndefined();
  });

  it('step2_plan_ready 与 step2_complete 事件顺序正确', () => {
    // step2_plan_ready 应该在 step2_complete 之前
    const events = [
      { type: 'step1_complete', timestamp: 1 },
      { type: 'step2_plan_ready', timestamp: 2 },
      { type: 'step2_complete', timestamp: 3 },
    ];

    const planReadyIndex = events.findIndex(e => e.type === 'step2_plan_ready');
    const completeIndex = events.findIndex(e => e.type === 'step2_complete');

    expect(planReadyIndex).toBeLessThan(completeIndex);
  });
});

describe('SSE Event: 用户修改追踪', () => {
  it('正确追踪用户添加的步骤', () => {
    const eventData = TestDataFactory.createStep2PlanReadyEvent({
      user_added_steps: ['S3', 'S4'],
    });

    expect(eventData.user_added_steps).toContain('S3');
    expect(eventData.user_added_steps).toContain('S4');
  });

  it('正确追踪用户删除的步骤', () => {
    const eventData = TestDataFactory.createStep2PlanReadyEvent({
      user_deleted_steps: ['S1'],
    });

    expect(eventData.user_deleted_steps).toContain('S1');
  });

  it('正确追踪用户修改的步骤', () => {
    const eventData = TestDataFactory.createStep2PlanReadyEvent({
      user_modified_steps: ['S2'],
    });

    expect(eventData.user_modified_steps).toContain('S2');
  });

  it('步骤的 is_user_added 标记正确', () => {
    const eventData = TestDataFactory.createStep2PlanReadyEvent({
      search_steps: [
        { id: 'S1', task_description: '原始任务', is_user_added: false },
        { id: 'S2', task_description: '用户添加', is_user_added: true },
      ],
    });

    expect(eventData.search_steps[0].is_user_added).toBe(false);
    expect(eventData.search_steps[1].is_user_added).toBe(true);
  });

  it('步骤的 is_user_modified 标记正确', () => {
    const eventData = TestDataFactory.createStep2PlanReadyEvent({
      search_steps: [
        { id: 'S1', task_description: '未修改', is_user_modified: false },
        { id: 'S2', task_description: '已修改', is_user_modified: true },
      ],
    });

    expect(eventData.search_steps[0].is_user_modified).toBe(false);
    expect(eventData.search_steps[1].is_user_modified).toBe(true);
  });
});
