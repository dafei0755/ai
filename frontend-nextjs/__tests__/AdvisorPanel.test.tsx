// frontend-nextjs/__tests__/AdvisorPanel.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { AdvisorPanel } from '@/components/project-cockpit/AdvisorPanel';
import { MOCK_ADVISOR_VIEW_MODEL } from '@/components/project-cockpit/mock/mockData';
import type { ActionChip } from '@/types/advisor';

describe('AdvisorPanel', () => {
  const mockOnChipAction = jest.fn();
  const mockOnAsk = jest.fn();

  beforeEach(() => {
    mockOnChipAction.mockClear();
    mockOnAsk.mockClear();
  });

  it('renders title "方案高参"', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('方案高参')).toBeInTheDocument();
  });

  it('renders module label in title bar', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText(/项目底盘/)).toBeInTheDocument();
  });

  it('renders evidenceStatus badge "内部推断"', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('内部推断')).toBeInTheDocument();
  });

  it('renders judgment content', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(
      screen.getByText(MOCK_ADVISOR_VIEW_MODEL.judgment.content)
    ).toBeInTheDocument();
  });

  it('renders primary chip label', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('补充 3 个关键信息')).toBeInTheDocument();
  });

  it('ask chip click fills textarea with question (does not call onChipAction)', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    fireEvent.click(screen.getByText('补充 3 个关键信息'));
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue(
      '请问项目总建筑面积大概是多少？客房数量和房型组合是什么？是否有平面图或现场照片？'
    );
    expect(mockOnChipAction).not.toHaveBeenCalled();
  });

  it('navigate chip click calls onChipAction with chip object', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    fireEvent.click(screen.getByText('预览平面推演'));
    expect(mockOnChipAction).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'navigate',
        payload: { target: 'floor_plan' },
      })
    );
  });

  it('fill chip click calls onChipAction', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    fireEvent.click(screen.getByText('保存项目方向草案'));
    expect(mockOnChipAction).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'fill' })
    );
  });

  it('renders 3 activated capabilities as placeholders', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('本体论')).toBeInTheDocument();
    expect(screen.getByText('方法论')).toBeInTheDocument();
    expect(screen.getByText('知识库')).toBeInTheDocument();
  });

  it('prefillMessage sets textarea value', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        prefillMessage="测试预填充"
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByRole('textbox')).toHaveValue('测试预填充');
  });

  it('renders cannotDo reason text', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(
      screen.getByText('缺少面积和平面图，无法启动空间推演')
    ).toBeInTheDocument();
  });
});
