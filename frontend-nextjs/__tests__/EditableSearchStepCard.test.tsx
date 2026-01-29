/**
 * v7.300: EditableSearchStepCard 组件单元测试
 *
 * 测试可编辑搜索步骤卡片：
 * 1. 组件渲染
 * 2. 编辑模式切换
 * 3. 保存/取消编辑
 * 4. 删除确认
 * 5. 状态显示
 * 6. 优先级和并行标记
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import type { EditableSearchStep } from '@/types';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Edit3: () => <span data-testid="edit-icon">Edit3</span>,
  Trash2: () => <span data-testid="trash-icon">Trash2</span>,
  Check: () => <span data-testid="check-icon">Check</span>,
  X: () => <span data-testid="x-icon">X</span>,
  GripVertical: () => <span data-testid="grip-icon">GripVertical</span>,
  Search: () => <span data-testid="search-icon">Search</span>,
  ChevronRight: () => <span data-testid="chevron-icon">ChevronRight</span>,
  Loader2: () => <span data-testid="loader-icon">Loader2</span>,
  CheckCircle: () => <span data-testid="check-circle-icon">CheckCircle</span>,
  Circle: () => <span data-testid="circle-icon">Circle</span>,
  Zap: () => <span data-testid="zap-icon">Zap</span>,
}));

import EditableSearchStepCard from '@/components/search/EditableSearchStepCard';

describe('EditableSearchStepCard', () => {
  // 测试数据工厂
  const createMockStep = (overrides: Partial<EditableSearchStep> = {}): EditableSearchStep => ({
    id: 'S1',
    step_number: 1,
    task_description: '搜索HAY品牌设计语言和核心特征',
    expected_outcome: '获取HAY品牌的色彩体系、材质偏好、设计理念',
    search_keywords: ['HAY', '北欧设计', '丹麦家居'],
    priority: 'high',
    can_parallel: true,
    status: 'pending',
    completion_score: 0,
    is_user_added: false,
    is_user_modified: false,
    ...overrides,
  });

  const defaultProps = {
    step: createMockStep(),
    onUpdate: jest.fn(),
    onDelete: jest.fn(),
    isReadOnly: false,
    showDragHandle: false,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('渲染测试', () => {
    it('正确渲染步骤编号', () => {
      render(<EditableSearchStepCard {...defaultProps} />);
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    it('正确渲染任务描述', () => {
      render(<EditableSearchStepCard {...defaultProps} />);
      expect(screen.getByText('搜索HAY品牌设计语言和核心特征')).toBeInTheDocument();
    });

    it('正确渲染期望结果', () => {
      render(<EditableSearchStepCard {...defaultProps} />);
      expect(screen.getByText(/获取HAY品牌的色彩体系/)).toBeInTheDocument();
    });

    it('正确渲染搜索关键词', () => {
      render(<EditableSearchStepCard {...defaultProps} />);
      expect(screen.getByText('HAY')).toBeInTheDocument();
      expect(screen.getByText('北欧设计')).toBeInTheDocument();
      expect(screen.getByText('丹麦家居')).toBeInTheDocument();
    });

    it('无期望结果时不显示期望区域', () => {
      const step = createMockStep({ expected_outcome: '' });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.queryByText('期望：')).not.toBeInTheDocument();
    });

    it('无关键词时不显示关键词区域', () => {
      const step = createMockStep({ search_keywords: [] });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.queryByText('HAY')).not.toBeInTheDocument();
    });
  });

  describe('优先级显示', () => {
    it('高优先级显示正确标签', () => {
      const step = createMockStep({ priority: 'high' });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByText('高优')).toBeInTheDocument();
    });

    it('中优先级显示正确标签', () => {
      const step = createMockStep({ priority: 'medium' });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByText('中优')).toBeInTheDocument();
    });

    it('低优先级显示正确标签', () => {
      const step = createMockStep({ priority: 'low' });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByText('低优')).toBeInTheDocument();
    });
  });

  describe('状态显示', () => {
    it('pending 状态显示空心圆', () => {
      const step = createMockStep({ status: 'pending' });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByTestId('circle-icon')).toBeInTheDocument();
    });

    it('searching 状态显示加载动画', () => {
      const step = createMockStep({ status: 'searching' });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();
    });

    it('complete 状态显示完成图标', () => {
      const step = createMockStep({ status: 'complete' });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
    });
  });

  describe('并行标记', () => {
    it('可并行时显示并行标记', () => {
      const step = createMockStep({ can_parallel: true });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByText('可并行')).toBeInTheDocument();
    });

    it('不可并行时不显示并行标记', () => {
      const step = createMockStep({ can_parallel: false });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.queryByText('可并行')).not.toBeInTheDocument();
    });
  });

  describe('用户修改标记', () => {
    it('用户添加的步骤显示"新增"标记', () => {
      const step = createMockStep({ is_user_added: true });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByText('新增')).toBeInTheDocument();
    });

    it('用户修改的步骤显示"已修改"标记', () => {
      const step = createMockStep({ is_user_modified: true, is_user_added: false });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByText('已修改')).toBeInTheDocument();
    });

    it('用户添加的步骤不显示"已修改"标记', () => {
      const step = createMockStep({ is_user_added: true, is_user_modified: true });
      render(<EditableSearchStepCard {...defaultProps} step={step} />);
      expect(screen.getByText('新增')).toBeInTheDocument();
      expect(screen.queryByText('已修改')).not.toBeInTheDocument();
    });
  });

  describe('编辑模式', () => {
    it('点击编辑按钮进入编辑模式', async () => {
      render(<EditableSearchStepCard {...defaultProps} />);

      // 悬停显示编辑按钮
      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);

      const editButton = screen.getByTestId('edit-icon').closest('button');
      fireEvent.click(editButton!);

      // 编辑模式下显示文本框
      await waitFor(() => {
        expect(screen.getByDisplayValue('搜索HAY品牌设计语言和核心特征')).toBeInTheDocument();
      });
    });

    it('编辑模式下可以修改任务描述', async () => {
      render(<EditableSearchStepCard {...defaultProps} />);

      // 进入编辑模式
      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);
      const editButton = screen.getByTestId('edit-icon').closest('button');
      fireEvent.click(editButton!);

      // 修改内容
      const textarea = screen.getByDisplayValue('搜索HAY品牌设计语言和核心特征');
      fireEvent.change(textarea, { target: { value: '修改后的任务描述' } });

      expect(screen.getByDisplayValue('修改后的任务描述')).toBeInTheDocument();
    });

    it('保存编辑触发 onUpdate', async () => {
      const mockOnUpdate = jest.fn();
      render(<EditableSearchStepCard {...defaultProps} onUpdate={mockOnUpdate} />);

      // 进入编辑模式
      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);
      const editButton = screen.getByTestId('edit-icon').closest('button');
      fireEvent.click(editButton!);

      // 修改并保存
      const textarea = screen.getByDisplayValue('搜索HAY品牌设计语言和核心特征');
      fireEvent.change(textarea, { target: { value: '修改后的任务' } });

      const saveButton = screen.getByTestId('check-icon').closest('button');
      fireEvent.click(saveButton!);

      expect(mockOnUpdate).toHaveBeenCalledWith('S1', {
        task_description: '修改后的任务',
        expected_outcome: '获取HAY品牌的色彩体系、材质偏好、设计理念',
      });
    });

    it('取消编辑恢复原内容', async () => {
      render(<EditableSearchStepCard {...defaultProps} />);

      // 进入编辑模式
      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);
      const editButton = screen.getByTestId('edit-icon').closest('button');
      fireEvent.click(editButton!);

      // 修改内容
      const textarea = screen.getByDisplayValue('搜索HAY品牌设计语言和核心特征');
      fireEvent.change(textarea, { target: { value: '修改后的任务' } });

      // 取消
      const cancelButton = screen.getByTestId('x-icon').closest('button');
      fireEvent.click(cancelButton!);

      // 恢复原内容
      await waitFor(() => {
        expect(screen.getByText('搜索HAY品牌设计语言和核心特征')).toBeInTheDocument();
      });
    });
  });

  describe('删除功能', () => {
    it('点击删除按钮显示确认对话框', async () => {
      render(<EditableSearchStepCard {...defaultProps} />);

      // 悬停显示删除按钮
      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);

      const deleteButton = screen.getByTestId('trash-icon').closest('button');
      fireEvent.click(deleteButton!);

      await waitFor(() => {
        expect(screen.getByText('确定删除这个搜索步骤吗？')).toBeInTheDocument();
      });
    });

    it('确认删除触发 onDelete', async () => {
      const mockOnDelete = jest.fn();
      render(<EditableSearchStepCard {...defaultProps} onDelete={mockOnDelete} />);

      // 点击删除
      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);
      const deleteButton = screen.getByTestId('trash-icon').closest('button');
      fireEvent.click(deleteButton!);

      // 确认删除
      await waitFor(() => {
        expect(screen.getByText('确定删除这个搜索步骤吗？')).toBeInTheDocument();
      });

      const confirmButton = screen.getByRole('button', { name: '删除' });
      fireEvent.click(confirmButton);

      expect(mockOnDelete).toHaveBeenCalledWith('S1');
    });

    it('取消删除关闭确认对话框', async () => {
      render(<EditableSearchStepCard {...defaultProps} />);

      // 点击删除
      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);
      const deleteButton = screen.getByTestId('trash-icon').closest('button');
      fireEvent.click(deleteButton!);

      // 取消
      await waitFor(() => {
        expect(screen.getByText('确定删除这个搜索步骤吗？')).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: '取消' });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText('确定删除这个搜索步骤吗？')).not.toBeInTheDocument();
      });
    });
  });

  describe('只读模式', () => {
    it('只读模式下不显示编辑按钮', () => {
      render(<EditableSearchStepCard {...defaultProps} isReadOnly={true} />);

      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);

      expect(screen.queryByTestId('edit-icon')).not.toBeInTheDocument();
      expect(screen.queryByTestId('trash-icon')).not.toBeInTheDocument();
    });
  });

  describe('拖拽手柄', () => {
    it('showDragHandle 为 true 时显示拖拽手柄', () => {
      render(<EditableSearchStepCard {...defaultProps} showDragHandle={true} />);

      const card = screen.getByText('搜索HAY品牌设计语言和核心特征').closest('div');
      fireEvent.mouseEnter(card!.parentElement!.parentElement!);

      expect(screen.getByTestId('grip-icon')).toBeInTheDocument();
    });

    it('只读模式下不显示拖拽手柄', () => {
      render(<EditableSearchStepCard {...defaultProps} showDragHandle={true} isReadOnly={true} />);
      expect(screen.queryByTestId('grip-icon')).not.toBeInTheDocument();
    });
  });

  describe('完成状态样式', () => {
    it('完成状态下卡片有透明度', () => {
      const step = createMockStep({ status: 'complete' });
      const { container } = render(<EditableSearchStepCard {...defaultProps} step={step} />);

      const card = container.firstChild as HTMLElement;
      expect(card.className).toContain('opacity-75');
    });
  });
});

describe('EditableSearchStep 边界情况测试', () => {
  const createMockStep = (overrides: Partial<EditableSearchStep> = {}): EditableSearchStep => ({
    id: 'S1',
    step_number: 1,
    task_description: '测试任务',
    expected_outcome: '',
    search_keywords: [],
    priority: 'medium',
    can_parallel: true,
    status: 'pending',
    completion_score: 0,
    ...overrides,
  });

  it('处理超长任务描述', () => {
    const longDescription = '这是一个非常长的任务描述'.repeat(20);
    const step = createMockStep({ task_description: longDescription });

    render(
      <EditableSearchStepCard
        step={step}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getByText(longDescription)).toBeInTheDocument();
  });

  it('处理特殊字符', () => {
    const specialChars = '搜索 <script>alert("xss")</script> & "引号" \'单引号\'';
    const step = createMockStep({ task_description: specialChars });

    render(
      <EditableSearchStepCard
        step={step}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getByText(specialChars)).toBeInTheDocument();
  });

  it('处理 Unicode 字符', () => {
    const unicodeText = '搜索 🎨 设计 🏠 民宿 🌿 自然';
    const step = createMockStep({ task_description: unicodeText });

    render(
      <EditableSearchStepCard
        step={step}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getByText(unicodeText)).toBeInTheDocument();
  });

  it('处理空字符串 ID', () => {
    const step = createMockStep({ id: '' });

    // 不应该抛出错误
    expect(() => {
      render(
        <EditableSearchStepCard
          step={step}
          onUpdate={jest.fn()}
          onDelete={jest.fn()}
        />
      );
    }).not.toThrow();
  });

  it('处理负数步骤编号', () => {
    const step = createMockStep({ step_number: -1 });

    render(
      <EditableSearchStepCard
        step={step}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getByText('-1')).toBeInTheDocument();
  });

  it('处理完成分数边界值', () => {
    const step = createMockStep({ completion_score: 1.0, status: 'complete' });

    render(
      <EditableSearchStepCard
        step={step}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
  });
});
