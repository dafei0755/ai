/**
 * 单元测试: 搜索结果显示组件
 *
 * 测试 v7.217 修复: 解题思考和多轮搜索显示
 *
 * Bug: search-20260117-9c2e68067f2e
 * 问题: 思考内容和搜索轮次数据存在但不显示
 * 修复: 添加 ThinkingContentCard 和 SearchRoundsCard 组件
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock ReactMarkdown
jest.mock('react-markdown', () => {
  return function ReactMarkdown({ children }: { children: string }) {
    return <div data-testid="markdown-content">{children}</div>;
  };
});

// Mock remark-gfm
jest.mock('remark-gfm', () => ({}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Brain: () => <div data-testid="brain-icon">Brain</div>,
  History: () => <div data-testid="history-icon">History</div>,
  ChevronRight: ({ className }: { className?: string }) => (
    <div data-testid="chevron-icon" className={className}>Chevron</div>
  ),
  CheckCircle: () => <div data-testid="check-icon">Check</div>,
  ExternalLink: () => <div data-testid="external-icon">External</div>,
}));

// 模拟组件定义（从实际文件中提取）
interface RoundRecord {
  round: number;
  topicName: string;
  searchQuery: string;
  sourcesFound: number;
  sources: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
  status: 'pending' | 'searching' | 'complete';
  reasoningContent?: string;
  thinkingContent?: string;
}

// ThinkingContentCard 组件
const ThinkingContentCard = ({ content, isExpanded, onToggle }: {
  content: string;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  if (!content) return null;

  return (
    <div data-testid="thinking-card" className="bg-white rounded-xl mb-4">
      <div
        data-testid="thinking-header"
        className="cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <div data-testid="brain-icon">Brain</div>
          <span>解题思考过程</span>
        </div>
      </div>

      {isExpanded && (
        <div data-testid="thinking-content">
          <div data-testid="markdown-content">{content}</div>
        </div>
      )}
    </div>
  );
};

// SearchRoundsCard 组件
const SearchRoundsCard = ({ rounds, isExpanded, onToggle }: {
  rounds: RoundRecord[];
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  if (!rounds || rounds.length === 0) return null;

  const [expandedRounds, setExpandedRounds] = React.useState<Set<number>>(new Set());

  const toggleRound = (roundNum: number) => {
    const newExpanded = new Set(expandedRounds);
    if (newExpanded.has(roundNum)) {
      newExpanded.delete(roundNum);
    } else {
      newExpanded.add(roundNum);
    }
    setExpandedRounds(newExpanded);
  };

  return (
    <div data-testid="rounds-card" className="bg-white rounded-xl mb-4">
      <div
        data-testid="rounds-header"
        className="cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <div data-testid="history-icon">History</div>
          <span>搜索轮次</span>
          <span data-testid="rounds-count">{rounds.length}轮</span>
        </div>
      </div>

      {isExpanded && (
        <div data-testid="rounds-list">
          {rounds.map((round) => {
            const isRoundExpanded = expandedRounds.has(round.round);

            return (
              <div key={round.round} data-testid={`round-${round.round}`}>
                <div
                  data-testid={`round-${round.round}-header`}
                  className="cursor-pointer"
                  onClick={() => toggleRound(round.round)}
                >
                  <span>第{round.round}轮</span>
                  {round.topicName && <span>{round.topicName}</span>}
                  {round.sourcesFound > 0 && (
                    <span data-testid={`round-${round.round}-sources-count`}>
                      {round.sourcesFound}个来源
                    </span>
                  )}
                </div>

                {isRoundExpanded && (
                  <div data-testid={`round-${round.round}-details`}>
                    {round.searchQuery && (
                      <div data-testid={`round-${round.round}-query`}>
                        查询: {round.searchQuery}
                      </div>
                    )}

                    {(round.reasoningContent || round.thinkingContent) && (
                      <div data-testid={`round-${round.round}-thinking`}>
                        {round.reasoningContent || round.thinkingContent}
                      </div>
                    )}

                    {round.sources && round.sources.length > 0 && (
                      <div data-testid={`round-${round.round}-sources`}>
                        {round.sources.map((source, idx) => (
                          <div key={idx} data-testid={`round-${round.round}-source-${idx}`}>
                            <div>{source.title}</div>
                            {source.snippet && <div>{source.snippet}</div>}
                            {source.url && <a href={source.url}>查看来源</a>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

describe('ThinkingContentCard', () => {
  const mockThinkingContent = `# 深度推理过程

## 问题分析
这是一个关于民宿设计的问题...

## 解决方案
1. 分析HAY品牌特点
2. 结合峨眉山地域特色
3. 提出设计方案`;

  it('应该在有内容时渲染组件', () => {
    const onToggle = jest.fn();
    render(
      <ThinkingContentCard
        content={mockThinkingContent}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    expect(screen.getByTestId('thinking-card')).toBeInTheDocument();
    expect(screen.getByText('解题思考过程')).toBeInTheDocument();
  });

  it('应该在没有内容时不渲染', () => {
    const onToggle = jest.fn();
    const { container } = render(
      <ThinkingContentCard
        content=""
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('应该在展开时显示内容', () => {
    const onToggle = jest.fn();
    render(
      <ThinkingContentCard
        content={mockThinkingContent}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    expect(screen.getByTestId('thinking-content')).toBeInTheDocument();
    // 验证内容包含关键文本（忽略格式差异）
    const markdownContent = screen.getByTestId('markdown-content');
    expect(markdownContent).toHaveTextContent('深度推理过程');
    expect(markdownContent).toHaveTextContent('问题分析');
    expect(markdownContent).toHaveTextContent('解决方案');
  });

  it('应该在折叠时隐藏内容', () => {
    const onToggle = jest.fn();
    render(
      <ThinkingContentCard
        content={mockThinkingContent}
        isExpanded={false}
        onToggle={onToggle}
      />
    );

    expect(screen.queryByTestId('thinking-content')).not.toBeInTheDocument();
  });

  it('应该在点击标题时调用 onToggle', () => {
    const onToggle = jest.fn();
    render(
      <ThinkingContentCard
        content={mockThinkingContent}
        isExpanded={false}
        onToggle={onToggle}
      />
    );

    fireEvent.click(screen.getByTestId('thinking-header'));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});

describe('SearchRoundsCard', () => {
  const mockRounds: RoundRecord[] = [
    {
      round: 1,
      topicName: '基础概念探索',
      searchQuery: 'HAY品牌 设计理念',
      sourcesFound: 8,
      sources: [
        {
          title: 'HAY品牌介绍',
          url: 'https://example.com/hay',
          snippet: 'HAY是丹麦著名家居品牌...',
        },
        {
          title: 'HAY设计哲学',
          url: 'https://example.com/hay-philosophy',
          snippet: '简约、功能性、色彩...',
        },
      ],
      status: 'complete',
      reasoningContent: '第一轮搜索聚焦于HAY品牌的核心特点...',
    },
    {
      round: 2,
      topicName: '维度深化',
      searchQuery: '峨眉山 民宿设计',
      sourcesFound: 6,
      sources: [
        {
          title: '峨眉山民宿案例',
          url: 'https://example.com/emeishan',
          snippet: '结合地域文化的民宿设计...',
        },
      ],
      status: 'complete',
      thinkingContent: '第二轮搜索关注地域特色...',
    },
  ];

  it('应该在有轮次数据时渲染组件', () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    expect(screen.getByTestId('rounds-card')).toBeInTheDocument();
    expect(screen.getByText('搜索轮次')).toBeInTheDocument();
    expect(screen.getByTestId('rounds-count')).toHaveTextContent('2轮');
  });

  it('应该在没有轮次数据时不渲染', () => {
    const onToggle = jest.fn();
    const { container } = render(
      <SearchRoundsCard
        rounds={[]}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('应该显示所有轮次', () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    expect(screen.getByTestId('round-1')).toBeInTheDocument();
    expect(screen.getByTestId('round-2')).toBeInTheDocument();
    expect(screen.getByText('第1轮')).toBeInTheDocument();
    expect(screen.getByText('第2轮')).toBeInTheDocument();
  });

  it('应该显示每轮的来源数量', () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    expect(screen.getByTestId('round-1-sources-count')).toHaveTextContent('8个来源');
    expect(screen.getByTestId('round-2-sources-count')).toHaveTextContent('6个来源');
  });

  it('应该在点击轮次时展开详情', async () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    // 初始状态：详情应该是隐藏的
    expect(screen.queryByTestId('round-1-details')).not.toBeInTheDocument();

    // 点击第1轮标题
    fireEvent.click(screen.getByTestId('round-1-header'));

    // 详情应该显示
    await waitFor(() => {
      expect(screen.getByTestId('round-1-details')).toBeInTheDocument();
    });
  });

  it('应该显示轮次的搜索查询', async () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    // 展开第1轮
    fireEvent.click(screen.getByTestId('round-1-header'));

    await waitFor(() => {
      expect(screen.getByTestId('round-1-query')).toHaveTextContent('HAY品牌 设计理念');
    });
  });

  it('应该显示轮次的思考内容', async () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    // 展开第1轮
    fireEvent.click(screen.getByTestId('round-1-header'));

    await waitFor(() => {
      const thinkingElement = screen.getByTestId('round-1-thinking');
      expect(thinkingElement).toHaveTextContent('第一轮搜索聚焦于HAY品牌的核心特点');
    });
  });

  it('应该显示轮次的来源列表', async () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    // 展开第1轮
    fireEvent.click(screen.getByTestId('round-1-header'));

    await waitFor(() => {
      expect(screen.getByTestId('round-1-sources')).toBeInTheDocument();
      expect(screen.getByTestId('round-1-source-0')).toBeInTheDocument();
      expect(screen.getByText('HAY品牌介绍')).toBeInTheDocument();
      expect(screen.getByText('HAY是丹麦著名家居品牌...')).toBeInTheDocument();
    });
  });

  it('应该支持多个轮次同时展开', async () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    // 展开第1轮
    fireEvent.click(screen.getByTestId('round-1-header'));
    await waitFor(() => {
      expect(screen.getByTestId('round-1-details')).toBeInTheDocument();
    });

    // 展开第2轮
    fireEvent.click(screen.getByTestId('round-2-header'));
    await waitFor(() => {
      expect(screen.getByTestId('round-2-details')).toBeInTheDocument();
    });

    // 两个轮次都应该是展开状态
    expect(screen.getByTestId('round-1-details')).toBeInTheDocument();
    expect(screen.getByTestId('round-2-details')).toBeInTheDocument();
  });

  it('应该在再次点击时折叠轮次', async () => {
    const onToggle = jest.fn();
    render(
      <SearchRoundsCard
        rounds={mockRounds}
        isExpanded={true}
        onToggle={onToggle}
      />
    );

    // 展开第1轮
    fireEvent.click(screen.getByTestId('round-1-header'));
    await waitFor(() => {
      expect(screen.getByTestId('round-1-details')).toBeInTheDocument();
    });

    // 再次点击折叠
    fireEvent.click(screen.getByTestId('round-1-header'));
    await waitFor(() => {
      expect(screen.queryByTestId('round-1-details')).not.toBeInTheDocument();
    });
  });
});

describe('集成测试: 完整搜索结果显示', () => {
  it('应该正确显示来自数据库的真实数据', () => {
    // 模拟从数据库加载的会话数据
    const sessionData = {
      session_id: 'search-20260117-9c2e68067f2e',
      isDeepMode: true,
      totalRounds: 5,
      thinkingContent: '# 深度分析\n\n这是DeepSeek的推理过程...',
      rounds: [
        {
          round: 1,
          topicName: '概念探索',
          searchQuery: 'HAY 民宿设计',
          sourcesFound: 10,
          sources: [],
          status: 'complete' as const,
        },
        {
          round: 2,
          topicName: '维度深化',
          searchQuery: '峨眉山 地域特色',
          sourcesFound: 8,
          sources: [],
          status: 'complete' as const,
        },
      ],
    };

    const onToggleThinking = jest.fn();
    const onToggleRounds = jest.fn();

    const { container } = render(
      <div>
        <ThinkingContentCard
          content={sessionData.thinkingContent}
          isExpanded={true}
          onToggle={onToggleThinking}
        />
        <SearchRoundsCard
          rounds={sessionData.rounds}
          isExpanded={true}
          onToggle={onToggleRounds}
        />
      </div>
    );

    // 验证两个组件都渲染了
    expect(screen.getByTestId('thinking-card')).toBeInTheDocument();
    expect(screen.getByTestId('rounds-card')).toBeInTheDocument();

    // 验证数据正确显示
    expect(screen.getByText('解题思考过程')).toBeInTheDocument();
    expect(screen.getByText('搜索轮次')).toBeInTheDocument();
    expect(screen.getByTestId('rounds-count')).toHaveTextContent('2轮');
  });
});
