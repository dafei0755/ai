import { existsSync } from 'fs';
import path from 'path';

import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const componentsRoot = __dirname;
const visualBriefPanelPath = path.join(componentsRoot, 'VisualBriefPanel.tsx');
const advisorContextPanelPath = path.join(componentsRoot, 'AdvisorContextPanel.tsx');

const loadPanelComponents = () => {
  expect(existsSync(visualBriefPanelPath)).toBe(true);
  expect(existsSync(advisorContextPanelPath)).toBe(true);

  const { VisualBriefPanel } = require('./VisualBriefPanel') as typeof import('./VisualBriefPanel');
  const { AdvisorContextPanel } = require('./AdvisorContextPanel') as typeof import('./AdvisorContextPanel');

  return { VisualBriefPanel, AdvisorContextPanel };
};

describe('conversation panel components', () => {
  it('renders collapsed visual brief summary and toggles pin', async () => {
    const user = userEvent.setup();
    const onExpand = jest.fn();
    const onCollapseAfterHover = jest.fn();
    const onTogglePinnedOpen = jest.fn();
    const { VisualBriefPanel } = loadPanelComponents();

    render(
      <VisualBriefPanel
        visualBriefContext={{
          space: '返乡民居',
          status: 'auto',
          summary: '回到故土后的身心安放',
          visualPrompt: 'old and new residence',
          appliedTags: ['故土', '身心安放'],
          lockedTags: ['童年记忆'],
          negativeConstraints: [],
          sourceTitles: ['访谈摘要'],
        }}
        expanded={false}
        pinnedOpen={false}
        onExpand={onExpand}
        onCollapseAfterHover={onCollapseAfterHover}
        onTogglePinnedOpen={onTogglePinnedOpen}
      />,
    );

    expect(screen.getByText('空间 VisualBrief · 返乡民居')).toBeInTheDocument();
    expect(screen.getByText('回到故土后的身心安放')).toBeInTheDocument();
    expect(screen.getByText('故土')).toBeInTheDocument();
    expect(screen.getByText('锁 童年记忆')).toBeInTheDocument();

    fireEvent.mouseEnter(screen.getByText('空间 VisualBrief · 返乡民居').closest('div')!);
    await user.click(screen.getByRole('button', { name: '固定展开 VisualBrief' }));

    expect(onExpand).toHaveBeenCalled();
    expect(onTogglePinnedOpen).toHaveBeenCalled();
  });

  it('renders advisor context insight chips and resize handle', async () => {
    const user = userEvent.setup();
    const onExpand = jest.fn();
    const onCollapseAfterHover = jest.fn();
    const onTogglePinnedOpen = jest.fn();
    const onStartResize = jest.fn();
    const { AdvisorContextPanel } = loadPanelComponents();

    render(
      <AdvisorContextPanel
        advisorSceneContext={{
          key: 'return-home-house',
          label: '返乡民居需求洞察',
          suggestion: '1. 50岁意味着人生阶段和功成名就后的回望',
          sceneRef: 'advisor-context',
        }}
        advisorInsightLines={[
          '1. 50岁意味着人生阶段和功成名就后的回望',
          '2. 背井离乡意味着故土怀念和衣锦还乡',
        ]}
        contextExpanded={false}
        contextPinnedOpen={false}
        contextPanePercent={28}
        onExpand={onExpand}
        onCollapseAfterHover={onCollapseAfterHover}
        onTogglePinnedOpen={onTogglePinnedOpen}
        onStartResize={onStartResize}
      />,
    );

    expect(screen.getByText('返乡民居需求洞察')).toBeInTheDocument();
    expect(screen.getByText('50岁意味着人生阶段和功成名就后的回望')).toBeInTheDocument();
    expect(screen.getByText('背井离乡意味着故土怀念和衣锦还乡')).toBeInTheDocument();

    fireEvent.mouseEnter(screen.getByText('返乡民居需求洞察').closest('div')!);
    await user.click(screen.getByRole('button', { name: '固定展开上下文' }));
    fireEvent.mouseDown(screen.getByRole('button', { name: '拖动调整上下文和聊天窗口高度' }));

    expect(onExpand).toHaveBeenCalled();
    expect(onTogglePinnedOpen).toHaveBeenCalled();
    expect(onStartResize).toHaveBeenCalled();
  });
});
