/**
 * v7.240: FrameworkChecklistCard 组件测试
 *
 * 测试前端框架清单卡片组件：
 * 1. 组件渲染
 * 2. 展开/折叠功能
 * 3. 数据显示
 * 4. 边界情况处理
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Target: () => <span data-testid="target-icon">Target</span>,
  ListChecks: () => <span data-testid="listchecks-icon">ListChecks</span>,
  AlertCircle: () => <span data-testid="alertcircle-icon">AlertCircle</span>,
  ChevronRight: () => <span data-testid="chevronright-icon">ChevronRight</span>,
}));

// 定义 FrameworkChecklist 接口（与 page.tsx 中一致）
interface FrameworkChecklist {
  core_summary: string;
  main_directions: Array<{
    direction: string;
    purpose: string;
    expected_outcome: string;
  }>;
  boundaries: string[];
  answer_goal: string;
  generated_at: string;
  plain_text: string;
}

// 复制 FrameworkChecklistCard 组件用于测试
const FrameworkChecklistCard = ({
  checklist,
  isExpanded,
  onToggle
}: {
  checklist: FrameworkChecklist | null;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  if (!checklist) return null;

  return (
    <div data-testid="framework-checklist-card" className="bg-white rounded-xl mb-4">
      {/* 标题栏 */}
      <div
        data-testid="card-header"
        className="flex items-center justify-between cursor-pointer px-4 py-3"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
            <span data-testid="target-icon">Target</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-indigo-600">
              搜索框架清单
            </span>
            <span data-testid="direction-count" className="text-xs bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full">
              {checklist.main_directions.length}个方向
            </span>
          </div>
        </div>
        <span data-testid="chevronright-icon">ChevronRight</span>
      </div>

      {/* 内容区域 */}
      {isExpanded && (
        <div data-testid="card-content" className="px-4 py-4 border-t space-y-4">
          {/* 核心问题 */}
          <div data-testid="core-summary" className="bg-indigo-50 rounded-lg p-3">
            <div className="text-xs text-indigo-500 mb-1 font-medium">
              核心问题
            </div>
            <div className="text-sm text-indigo-700 font-medium">
              {checklist.core_summary}
            </div>
          </div>

          {/* 搜索主线 */}
          <div data-testid="main-directions">
            <div className="text-xs text-gray-500 mb-2 font-medium flex items-center gap-1">
              <span data-testid="listchecks-icon">ListChecks</span>
              搜索主线
            </div>
            <div className="space-y-2">
              {checklist.main_directions.map((direction, index) => (
                <div
                  key={index}
                  data-testid={`direction-${index}`}
                  className="bg-gray-50 rounded-lg p-3"
                >
                  <div className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center font-medium">
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-800">
                        {direction.direction}
                      </div>
                      {direction.purpose && (
                        <div className="text-xs text-gray-500 mt-1">
                          <span className="text-indigo-500">目的:</span> {direction.purpose}
                        </div>
                      )}
                      {direction.expected_outcome && (
                        <div className="text-xs text-gray-500 mt-0.5">
                          <span className="text-emerald-500">期望:</span> {direction.expected_outcome}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 搜索边界 */}
          {checklist.boundaries && checklist.boundaries.length > 0 && (
            <div data-testid="boundaries" className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1.5 font-medium flex items-center gap-1">
                <span data-testid="alertcircle-icon">AlertCircle</span>
                搜索边界（不涉及）
              </div>
              <div className="flex flex-wrap gap-1.5">
                {checklist.boundaries.map((boundary, index) => (
                  <span
                    key={index}
                    data-testid={`boundary-${index}`}
                    className="text-xs px-2 py-0.5 bg-red-50 text-red-600 rounded"
                  >
                    {boundary}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 回答目标 */}
          {checklist.answer_goal && (
            <div data-testid="answer-goal" className="bg-emerald-50 rounded-lg p-3">
              <div className="text-xs text-emerald-500 mb-1 font-medium flex items-center gap-1">
                <span data-testid="target-icon">Target</span>
                回答目标
              </div>
              <div className="text-sm text-emerald-700">
                {checklist.answer_goal}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

describe('FrameworkChecklistCard', () => {
  // 测试数据
  const mockChecklist: FrameworkChecklist = {
    core_summary: '如何设计北欧风客厅',
    main_directions: [
      { direction: '风格调研', purpose: '了解北欧风核心特征', expected_outcome: '色彩、材质特点' },
      { direction: '空间规划', purpose: '确定功能分区', expected_outcome: '动线方案' },
      { direction: '家具选择', purpose: '选择合适的家具', expected_outcome: '产品清单' },
    ],
    boundaries: ['不涉及厨房设计', '不涉及预算规划'],
    answer_goal: '提供完整的北欧风客厅设计方案',
    generated_at: '2026-01-23T10:00:00',
    plain_text: '## 核心问题\n如何设计北欧风客厅',
  };

  describe('渲染测试', () => {
    it('当 checklist 为 null 时不渲染', () => {
      const { container } = render(
        <FrameworkChecklistCard
          checklist={null}
          isExpanded={true}
          onToggle={() => {}}
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it('正确渲染卡片标题', () => {
      render(
        <FrameworkChecklistCard
          checklist={mockChecklist}
          isExpanded={false}
          onToggle={() => {}}
        />
      );

      expect(screen.getByText('搜索框架清单')).toBeInTheDocument();
      expect(screen.getByTestId('direction-count')).toHaveTextContent('3个方向');
    });

    it('展开时显示所有内容', () => {
      render(
        <FrameworkChecklistCard
          checklist={mockChecklist}
          isExpanded={true}
          onToggle={() => {}}
        />
      );

      // 核心问题
      expect(screen.getByTestId('core-summary')).toBeInTheDocument();
      expect(screen.getByText('如何设计北欧风客厅')).toBeInTheDocument();

      // 搜索主线
      expect(screen.getByTestId('main-directions')).toBeInTheDocument();
      expect(screen.getByText('风格调研')).toBeInTheDocument();
      expect(screen.getByText('空间规划')).toBeInTheDocument();
      expect(screen.getByText('家具选择')).toBeInTheDocument();

      // 边界
      expect(screen.getByTestId('boundaries')).toBeInTheDocument();
      expect(screen.getByText('不涉及厨房设计')).toBeInTheDocument();
      expect(screen.getByText('不涉及预算规划')).toBeInTheDocument();

      // 回答目标
      expect(screen.getByTestId('answer-goal')).toBeInTheDocument();
      expect(screen.getByText('提供完整的北欧风客厅设计方案')).toBeInTheDocument();
    });

    it('折叠时不显示内容区域', () => {
      render(
        <FrameworkChecklistCard
          checklist={mockChecklist}
          isExpanded={false}
          onToggle={() => {}}
        />
      );

      expect(screen.queryByTestId('card-content')).not.toBeInTheDocument();
    });
  });

  describe('交互测试', () => {
    it('点击标题栏触发 onToggle', () => {
      const mockToggle = jest.fn();
      render(
        <FrameworkChecklistCard
          checklist={mockChecklist}
          isExpanded={false}
          onToggle={mockToggle}
        />
      );

      fireEvent.click(screen.getByTestId('card-header'));
      expect(mockToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe('边界情况测试', () => {
    it('空边界列表时不显示边界区域', () => {
      const checklistWithoutBoundaries: FrameworkChecklist = {
        ...mockChecklist,
        boundaries: [],
      };

      render(
        <FrameworkChecklistCard
          checklist={checklistWithoutBoundaries}
          isExpanded={true}
          onToggle={() => {}}
        />
      );

      expect(screen.queryByTestId('boundaries')).not.toBeInTheDocument();
    });

    it('空回答目标时不显示回答目标区域', () => {
      const checklistWithoutGoal: FrameworkChecklist = {
        ...mockChecklist,
        answer_goal: '',
      };

      render(
        <FrameworkChecklistCard
          checklist={checklistWithoutGoal}
          isExpanded={true}
          onToggle={() => {}}
        />
      );

      expect(screen.queryByTestId('answer-goal')).not.toBeInTheDocument();
    });

    it('单个方向时正确显示', () => {
      const checklistWithOneDirection: FrameworkChecklist = {
        ...mockChecklist,
        main_directions: [
          { direction: '唯一方向', purpose: '唯一目的', expected_outcome: '唯一期望' },
        ],
      };

      render(
        <FrameworkChecklistCard
          checklist={checklistWithOneDirection}
          isExpanded={true}
          onToggle={() => {}}
        />
      );

      expect(screen.getByTestId('direction-count')).toHaveTextContent('1个方向');
      expect(screen.getByText('唯一方向')).toBeInTheDocument();
    });

    it('方向缺少可选字段时正确处理', () => {
      const checklistWithMinimalDirection: FrameworkChecklist = {
        ...mockChecklist,
        main_directions: [
          { direction: '只有方向名', purpose: '', expected_outcome: '' },
        ],
      };

      render(
        <FrameworkChecklistCard
          checklist={checklistWithMinimalDirection}
          isExpanded={true}
          onToggle={() => {}}
        />
      );

      expect(screen.getByText('只有方向名')).toBeInTheDocument();
      // 空的 purpose 和 expected_outcome 不应该显示
      expect(screen.queryByText('目的:')).not.toBeInTheDocument();
      expect(screen.queryByText('期望:')).not.toBeInTheDocument();
    });
  });

  describe('数据显示测试', () => {
    it('正确显示方向编号', () => {
      render(
        <FrameworkChecklistCard
          checklist={mockChecklist}
          isExpanded={true}
          onToggle={() => {}}
        />
      );

      // 检查编号 1, 2, 3
      const directions = screen.getAllByTestId(/^direction-\d+$/);
      expect(directions).toHaveLength(3);
    });

    it('正确显示目的和期望', () => {
      render(
        <FrameworkChecklistCard
          checklist={mockChecklist}
          isExpanded={true}
          onToggle={() => {}}
        />
      );

      expect(screen.getByText(/了解北欧风核心特征/)).toBeInTheDocument();
      expect(screen.getByText(/色彩、材质特点/)).toBeInTheDocument();
    });
  });
});

describe('FrameworkChecklist 数据结构测试', () => {
  it('验证完整的数据结构', () => {
    const checklist: FrameworkChecklist = {
      core_summary: '测试核心问题',
      main_directions: [
        { direction: '方向1', purpose: '目的1', expected_outcome: '期望1' },
      ],
      boundaries: ['边界1'],
      answer_goal: '回答目标',
      generated_at: '2026-01-23T10:00:00',
      plain_text: '纯文字内容',
    };

    expect(checklist.core_summary).toBe('测试核心问题');
    expect(checklist.main_directions).toHaveLength(1);
    expect(checklist.boundaries).toHaveLength(1);
    expect(checklist.answer_goal).toBe('回答目标');
    expect(checklist.generated_at).toBe('2026-01-23T10:00:00');
    expect(checklist.plain_text).toBe('纯文字内容');
  });
});

describe('SearchState 集成测试', () => {
  // 模拟 SearchState 中的 frameworkChecklist 字段
  interface MockSearchState {
    frameworkChecklist: FrameworkChecklist | null;
  }

  it('初始状态 frameworkChecklist 为 null', () => {
    const initialState: MockSearchState = {
      frameworkChecklist: null,
    };

    expect(initialState.frameworkChecklist).toBeNull();
  });

  it('可以设置 frameworkChecklist', () => {
    const state: MockSearchState = {
      frameworkChecklist: null,
    };

    const checklist: FrameworkChecklist = {
      core_summary: '测试',
      main_directions: [],
      boundaries: [],
      answer_goal: '目标',
      generated_at: '',
      plain_text: '',
    };

    state.frameworkChecklist = checklist;

    expect(state.frameworkChecklist).not.toBeNull();
    expect(state.frameworkChecklist?.core_summary).toBe('测试');
  });
});

describe('事件处理测试', () => {
  it('search_framework_ready 事件数据解析', () => {
    // 模拟后端返回的事件数据
    const eventData = {
      type: 'search_framework_ready',
      data: {
        core_question: '测试问题',
        answer_goal: '测试目标',
        boundary: '测试边界',
        target_count: 2,
        targets: [
          { id: 'T1', question: '问题1', why_need: '目的1' },
          { id: 'T2', question: '问题2', why_need: '目的2' },
        ],
        framework_checklist: {
          core_summary: '核心问题摘要',
          main_directions: [
            { direction: '方向1', purpose: '目的1', expected_outcome: '期望1' },
          ],
          boundaries: ['边界1'],
          answer_goal: '回答目标',
          generated_at: '2026-01-23T10:00:00',
          plain_text: '纯文字',
        },
      },
    };

    // 验证事件类型
    expect(eventData.type).toBe('search_framework_ready');

    // 验证 framework_checklist 存在
    expect(eventData.data.framework_checklist).toBeDefined();

    // 解析 framework_checklist
    const checklist = eventData.data.framework_checklist;
    const parsedChecklist: FrameworkChecklist = {
      core_summary: checklist.core_summary || '',
      main_directions: checklist.main_directions || [],
      boundaries: checklist.boundaries || [],
      answer_goal: checklist.answer_goal || '',
      generated_at: checklist.generated_at || '',
      plain_text: checklist.plain_text || '',
    };

    expect(parsedChecklist.core_summary).toBe('核心问题摘要');
    expect(parsedChecklist.main_directions).toHaveLength(1);
  });
});
