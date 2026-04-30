import { render, screen } from '@testing-library/react';
import ProgressBadge from '@/components/ProgressBadge';

describe('ProgressBadge', () => {
  it('should render with default progress of 0%', () => {
    render(<ProgressBadge />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('should render progress percentage correctly', () => {
    render(<ProgressBadge progress={0.45} />);
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('should round progress to nearest integer', () => {
    render(<ProgressBadge progress={0.456} />);
    expect(screen.getByText('46%')).toBeInTheDocument();
  });

  it('should display current stage when provided', () => {
    render(<ProgressBadge progress={0.6} currentStage="需求分析" />);
    expect(screen.getByText('60% | 需求分析')).toBeInTheDocument();
  });

  it('should not display stage separator when no currentStage', () => {
    render(<ProgressBadge progress={0.3} />);
    const text = screen.getByText('30%');
    expect(text.textContent).toBe('30%');
    expect(text.textContent).not.toContain('|');
  });

  it('should handle 100% progress', () => {
    render(<ProgressBadge progress={1.0} currentStage="完成" />);
    expect(screen.getByText('100% | 完成')).toBeInTheDocument();
  });

  it('should apply correct CSS classes', () => {
    const { container } = render(<ProgressBadge progress={0.5} />);
    const badge = container.querySelector('span');
    expect(badge).toHaveClass('text-xs', 'text-gray-500');
  });
});
