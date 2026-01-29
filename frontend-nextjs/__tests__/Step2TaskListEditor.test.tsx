/**
 * v7.300: Step2TaskListEditor 组件单元测试
 *
 * 测试可编辑搜索任务列表编辑器：
 * 1. 组件渲染
 * 2. 任务编辑功能
 * 3. 任务添加/删除
 * 4. 分页功能
 * 5. 智能建议功能
 * 6. 运行按钮交互
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import type { Step2SearchPlan, EditableSearchStep, SearchPlanSuggestion } from '@/types';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Plus: () => <span data-testid="plus-icon">Plus</span>,
  Play: () => <span data-testid="play-icon">Play</span>,
  ChevronLeft: () => <span data-testid="chevron-left-icon">ChevronLeft</span>,
  ChevronRight: () => <span data-testid="chevron-right-icon">ChevronRight</span>,
  Zap: () => <span data-testid="zap-icon">Zap</span>,
  ListChecks: () => <span data-testid="list-checks-icon">ListChecks</span>,
  AlertCircle: () => <span data-testid="alert-circle-icon">AlertCircle</span>,
  Loader2: () => <span data-testid="loader-icon">Loader2</span>,
  Check: () => <span data-testid="check-icon">Check</span>,
  X: () => <span data-testid="x-icon">X</span>,
}));

// Mock EditableSearchStepCard component
jest.mock('@/components/search/EditableSearchStepCard', () => {
  return function MockEditableSearchStepCard({
    step,
    onUpdate,
    onDelete,
    isReadOnly,
  }: {
    step: EditableSearchStep;
    onUpdate: (stepId: string, updates: Partial<EditableSearchStep>) => void;
    onDelete: (stepId: string) => void;
    isReadOnly?: boolean;
  }) {
    return (
      <div data-testid={`step-card-${step.id}`}>
        <span data-testid={`step-description-${step.id}`}>{step.task_description}</span>
        <span data-testid={`step-status-${step.id}`}>{step.status}</span>
        {!isReadOnly && (
          <>
            <button
              data-testid={`edit-btn-${step.id}`}
              onClick={() => onUpdate(step.id, { task_description: 'Updated' })}
            >
              Edit
            </button>
            <button
              data-testid={`delete-btn-${step.id}`}
              onClick={() => onDelete(step.id)}
            >
              Delete
            </button>
          </>
        )}
      </div>
    );
  };
});

// 复制 Step2TaskListEditor 组件核心逻辑用于测试
// 注意：实际测试中应该直接导入组件
import Step2TaskListEditor from '@/components/search/Step2TaskListEditor';

describe('Step2TaskListEditor', () => {
  // 测试数据工厂
  const createMockStep = (overrides: Partial<EditableSearchStep> = {}): EditableSearchStep => ({
    id: 'S1',
    step_number: 1,
    task_description: '搜索HAY品牌设计语言',
    expected_outcome: '获取HAY品牌核心设计特征',
    search_keywords: ['HAY', '北欧设计'],
    priority: 'high',
    can_parallel: true,
    status: 'pending',
    completion_score: 0,
    is_user_added: false,
    is_user_modified: false,
    ...overrides,
  });

  const createMockPlan = (overrides: Partial<Step2SearchPlan> = {}): Step2SearchPlan => ({
    session_id: 'test-session-123',
    query: '以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计',
    core_question: '如何融合HAY品牌气质与峨眉山地域特色',
    answer_goal: '提供完整的民宿室内概念设计方案',
    search_steps: [
      createMockStep({ id: 'S1', step_number: 1, task_description: '搜索HAY品牌设计语言' }),
      createMockStep({ id: 'S2', step_number: 2, task_description: '研究峨眉山七里坪地域特色' }),
      createMockStep({ id: 'S3', step_number: 3, task_description: '分析北欧与川西风格融合案例' }),
    ],
    max_rounds_per_step: 3,
    quality_threshold: 0.7,
    user_added_steps: [],
    user_deleted_steps: [],
    user_modified_steps: [],
    current_page: 1,
    total_pages: 1,
    is_confirmed: false,
    ...overrides,
  });

  const mockSuggestions: SearchPlanSuggestion[] = [
    {
      direction: '材质与工艺研究',
      what_to_search: '搜索HAY常用材质和峨眉山本地工艺',
      why_important: '材质选择是设计落地的关键',
      priority: 'P1',
    },
    {
      direction: '色彩体系分析',
      what_to_search: '分析HAY色彩体系与川西自然色彩',
      why_important: '色彩是风格融合的重要载体',
      priority: 'P0',
    },
  ];

  describe('渲染测试', () => {
    it('正确渲染组件标题和任务数量', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      expect(screen.getByText('搜索任务清单')).toBeInTheDocument();
      expect(screen.getByText(/共 3 个任务/)).toBeInTheDocument();
    });

    it('渲染所有搜索步骤卡片', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      expect(screen.getByTestId('step-card-S1')).toBeInTheDocument();
      expect(screen.getByTestId('step-card-S2')).toBeInTheDocument();
      expect(screen.getByTestId('step-card-S3')).toBeInTheDocument();
    });

    it('空任务列表时显示空状态', () => {
      const emptyPlan = createMockPlan({ search_steps: [] });
      render(
        <Step2TaskListEditor
          plan={emptyPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      expect(screen.getByText('暂无搜索任务')).toBeInTheDocument();
      expect(screen.getByText('点击下方按钮添加任务')).toBeInTheDocument();
    });

    it('显示并行任务指示器', () => {
      const mockPlan = createMockPlan({
        search_steps: [
          createMockStep({ id: 'S1', can_parallel: true, status: 'pending' }),
          createMockStep({ id: 'S2', can_parallel: true, status: 'pending' }),
          createMockStep({ id: 'S3', can_parallel: false, status: 'pending' }),
        ],
      });
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      expect(screen.getByText(/并行处理 2 个节点/)).toBeInTheDocument();
    });

    it('只读模式下隐藏编辑按钮', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
          isReadOnly={true}
        />
      );

      expect(screen.queryByText('添加任务')).not.toBeInTheDocument();
      expect(screen.queryByText('运行')).not.toBeInTheDocument();
    });
  });

  describe('任务编辑功能', () => {
    it('点击编辑按钮触发 onUpdatePlan', () => {
      const mockOnUpdatePlan = jest.fn();
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={mockOnUpdatePlan}
          onConfirmAndStart={jest.fn()}
        />
      );

      fireEvent.click(screen.getByTestId('edit-btn-S1'));

      expect(mockOnUpdatePlan).toHaveBeenCalled();
      const updatedPlan = mockOnUpdatePlan.mock.calls[0][0];
      expect(updatedPlan.user_modified_steps).toContain('S1');
    });

    it('点击删除按钮触发 onUpdatePlan 并移除步骤', () => {
      const mockOnUpdatePlan = jest.fn();
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={mockOnUpdatePlan}
          onConfirmAndStart={jest.fn()}
        />
      );

      fireEvent.click(screen.getByTestId('delete-btn-S2'));

      expect(mockOnUpdatePlan).toHaveBeenCalled();
      const updatedPlan = mockOnUpdatePlan.mock.calls[0][0];
      expect(updatedPlan.search_steps).toHaveLength(2);
      expect(updatedPlan.user_deleted_steps).toContain('S2');
    });
  });

  describe('添加任务功能', () => {
    it('点击添加任务按钮显示表单', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      fireEvent.click(screen.getByText('添加任务'));

      expect(screen.getByPlaceholderText('描述要搜索的内容...')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('期望获得什么信息...')).toBeInTheDocument();
    });

    it('填写表单并添加新任务', () => {
      const mockOnUpdatePlan = jest.fn();
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={mockOnUpdatePlan}
          onConfirmAndStart={jest.fn()}
        />
      );

      // 打开添加表单
      fireEvent.click(screen.getByText('添加任务'));

      // 填写表单
      const descriptionInput = screen.getByPlaceholderText('描述要搜索的内容...');
      const outcomeInput = screen.getByPlaceholderText('期望获得什么信息...');

      fireEvent.change(descriptionInput, { target: { value: '新的搜索任务' } });
      fireEvent.change(outcomeInput, { target: { value: '期望获得新信息' } });

      // 点击添加按钮
      fireEvent.click(screen.getByRole('button', { name: '添加' }));

      expect(mockOnUpdatePlan).toHaveBeenCalled();
      const updatedPlan = mockOnUpdatePlan.mock.calls[0][0];
      expect(updatedPlan.search_steps).toHaveLength(4);
      expect(updatedPlan.user_added_steps).toContain('S4');
    });

    it('空描述时添加按钮禁用', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      fireEvent.click(screen.getByText('添加任务'));

      const addButton = screen.getByRole('button', { name: '添加' });
      expect(addButton).toBeDisabled();
    });

    it('取消添加关闭表单', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      fireEvent.click(screen.getByText('添加任务'));
      expect(screen.getByPlaceholderText('描述要搜索的内容...')).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: '取消' }));
      expect(screen.queryByPlaceholderText('描述要搜索的内容...')).not.toBeInTheDocument();
    });
  });

  describe('分页功能', () => {
    it('超过5个任务时显示分页', () => {
      const manySteps = Array.from({ length: 8 }, (_, i) =>
        createMockStep({ id: `S${i + 1}`, step_number: i + 1, task_description: `任务 ${i + 1}` })
      );
      const mockPlan = createMockPlan({ search_steps: manySteps });

      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      expect(screen.getByText('1 / 2')).toBeInTheDocument();
    });

    it('点击下一页切换页面', () => {
      const manySteps = Array.from({ length: 8 }, (_, i) =>
        createMockStep({ id: `S${i + 1}`, step_number: i + 1, task_description: `任务 ${i + 1}` })
      );
      const mockPlan = createMockPlan({ search_steps: manySteps });

      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      // 第一页显示任务1-5
      expect(screen.getByTestId('step-card-S1')).toBeInTheDocument();
      expect(screen.getByTestId('step-card-S5')).toBeInTheDocument();
      expect(screen.queryByTestId('step-card-S6')).not.toBeInTheDocument();

      // 点击下一页
      fireEvent.click(screen.getByTestId('chevron-right-icon').parentElement!);

      // 第二页显示任务6-8
      expect(screen.queryByTestId('step-card-S1')).not.toBeInTheDocument();
      expect(screen.getByTestId('step-card-S6')).toBeInTheDocument();
      expect(screen.getByText('2 / 2')).toBeInTheDocument();
    });

    it('第一页时上一页按钮禁用', () => {
      const manySteps = Array.from({ length: 8 }, (_, i) =>
        createMockStep({ id: `S${i + 1}`, step_number: i + 1 })
      );
      const mockPlan = createMockPlan({ search_steps: manySteps });

      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      const prevButton = screen.getByTestId('chevron-left-icon').parentElement!;
      expect(prevButton).toBeDisabled();
    });
  });

  describe('智能建议功能', () => {
    it('验证后显示建议', async () => {
      const mockValidate = jest.fn().mockResolvedValue({
        has_suggestions: true,
        suggestions: mockSuggestions,
      });
      const mockPlan = createMockPlan();

      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
          onValidate={mockValidate}
        />
      );

      fireEvent.click(screen.getByText('运行'));

      await waitFor(() => {
        expect(screen.getByText('发现可能遗漏的搜索方向')).toBeInTheDocument();
      });

      expect(screen.getByText('材质与工艺研究')).toBeInTheDocument();
      expect(screen.getByText('色彩体系分析')).toBeInTheDocument();
    });

    it('从建议添加任务', async () => {
      const mockOnUpdatePlan = jest.fn();
      const mockValidate = jest.fn().mockResolvedValue({
        has_suggestions: true,
        suggestions: mockSuggestions,
      });
      const mockPlan = createMockPlan();

      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={mockOnUpdatePlan}
          onConfirmAndStart={jest.fn()}
          onValidate={mockValidate}
        />
      );

      fireEvent.click(screen.getByText('运行'));

      await waitFor(() => {
        expect(screen.getByText('材质与工艺研究')).toBeInTheDocument();
      });

      // 点击添加建议
      const addButtons = screen.getAllByRole('button', { name: '添加' });
      fireEvent.click(addButtons[0]);

      expect(mockOnUpdatePlan).toHaveBeenCalled();
    });

    it('忽略建议直接运行', async () => {
      const mockOnConfirmAndStart = jest.fn();
      const mockValidate = jest.fn().mockResolvedValue({
        has_suggestions: true,
        suggestions: mockSuggestions,
      });
      const mockPlan = createMockPlan();

      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={mockOnConfirmAndStart}
          onValidate={mockValidate}
        />
      );

      fireEvent.click(screen.getByText('运行'));

      await waitFor(() => {
        expect(screen.getByText('忽略并运行')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('忽略并运行'));

      expect(mockOnConfirmAndStart).toHaveBeenCalled();
    });

    it('无建议时直接运行', async () => {
      const mockOnConfirmAndStart = jest.fn();
      const mockValidate = jest.fn().mockResolvedValue({
        has_suggestions: false,
        suggestions: [],
      });
      const mockPlan = createMockPlan();

      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={mockOnConfirmAndStart}
          onValidate={mockValidate}
        />
      );

      fireEvent.click(screen.getByText('运行'));

      await waitFor(() => {
        expect(mockOnConfirmAndStart).toHaveBeenCalled();
      });
    });
  });

  describe('运行按钮状态', () => {
    it('空任务列表时运行按钮禁用', () => {
      const emptyPlan = createMockPlan({ search_steps: [] });
      render(
        <Step2TaskListEditor
          plan={emptyPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
        />
      );

      const runButton = screen.getByText('运行').closest('button');
      expect(runButton).toBeDisabled();
    });

    it('确认中显示加载状态', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
          isConfirming={true}
        />
      );

      expect(screen.getByText('启动中...')).toBeInTheDocument();
    });

    it('验证中显示检查状态', () => {
      const mockPlan = createMockPlan();
      render(
        <Step2TaskListEditor
          plan={mockPlan}
          onUpdatePlan={jest.fn()}
          onConfirmAndStart={jest.fn()}
          isValidating={true}
        />
      );

      expect(screen.getByText('检查中...')).toBeInTheDocument();
    });
  });
});

describe('Step2SearchPlan 数据结构测试', () => {
  it('验证完整的数据结构', () => {
    const plan: Step2SearchPlan = {
      session_id: 'test-123',
      query: '测试查询',
      core_question: '核心问题',
      answer_goal: '回答目标',
      search_steps: [
        {
          id: 'S1',
          step_number: 1,
          task_description: '任务描述',
          expected_outcome: '期望结果',
          search_keywords: ['关键词1'],
          priority: 'high',
          can_parallel: true,
          status: 'pending',
          completion_score: 0,
          is_user_added: false,
          is_user_modified: false,
        },
      ],
      max_rounds_per_step: 3,
      quality_threshold: 0.7,
      user_added_steps: [],
      user_deleted_steps: [],
      user_modified_steps: [],
      current_page: 1,
      total_pages: 1,
      is_confirmed: false,
    };

    expect(plan.session_id).toBe('test-123');
    expect(plan.search_steps).toHaveLength(1);
    expect(plan.search_steps[0].priority).toBe('high');
  });
});

describe('EditableSearchStep 数据结构测试', () => {
  it('验证步骤优先级类型', () => {
    const highPriority: EditableSearchStep = {
      id: 'S1',
      step_number: 1,
      task_description: '高优先级任务',
      expected_outcome: '',
      search_keywords: [],
      priority: 'high',
      can_parallel: true,
      status: 'pending',
      completion_score: 0,
    };

    const mediumPriority: EditableSearchStep = {
      ...highPriority,
      id: 'S2',
      priority: 'medium',
    };

    const lowPriority: EditableSearchStep = {
      ...highPriority,
      id: 'S3',
      priority: 'low',
    };

    expect(highPriority.priority).toBe('high');
    expect(mediumPriority.priority).toBe('medium');
    expect(lowPriority.priority).toBe('low');
  });

  it('验证步骤状态类型', () => {
    const pendingStep: EditableSearchStep = {
      id: 'S1',
      step_number: 1,
      task_description: '待执行',
      expected_outcome: '',
      search_keywords: [],
      priority: 'medium',
      can_parallel: true,
      status: 'pending',
      completion_score: 0,
    };

    const searchingStep: EditableSearchStep = {
      ...pendingStep,
      status: 'searching',
    };

    const completeStep: EditableSearchStep = {
      ...pendingStep,
      status: 'complete',
      completion_score: 0.85,
    };

    expect(pendingStep.status).toBe('pending');
    expect(searchingStep.status).toBe('searching');
    expect(completeStep.status).toBe('complete');
    expect(completeStep.completion_score).toBe(0.85);
  });
});
