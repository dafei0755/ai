import { render, screen } from '@testing-library/react';
import Step1DeepAnalysis from '../Step1DeepAnalysis';

describe('Step1DeepAnalysis', () => {
  const mockV2Output = `
**【深入研究计划】**

步骤 1 明确项目核心判断

✅ 先确认场地、客群与品牌气质之间的关系。

---

**【我们如何理解您的需求】**

🎯 我们理解您的核心需求：

**您想要的效果：**
• 融入HAY设计美学
`;

  it('should render the current two-section analysis format', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getByText(/深入研究计划/)).toBeInTheDocument();
    expect(screen.getByText(/我们如何理解您的需求/)).toBeInTheDocument();
  });

  it('should display research plan section with visual markers', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getAllByText(/🔬/)[0]).toBeInTheDocument();
    expect(screen.getByText(/明确项目核心判断/)).toBeInTheDocument();
    expect(screen.getByText(/先确认场地、客群与品牌气质之间的关系/)).toBeInTheDocument();
  });

  it('should display step headings', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText(/明确项目核心判断/)).toBeInTheDocument();
  });

  it('should display understanding section with target emoji', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getAllByText(/🎯/)[0]).toBeInTheDocument();
    expect(screen.getByText(/您想要的效果/)).toBeInTheDocument();
  });

  it('should have proper ARIA labels', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getByRole('region', { name: /深入研究计划/ })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /我们如何理解您的需求/ })).toBeInTheDocument();
  });

  it('should display loading state', () => {
    render(<Step1DeepAnalysis content="" isLoading={true} />);

    expect(screen.getByText(/正在分析/)).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should display error state', () => {
    render(<Step1DeepAnalysis content="" error="分析失败" />);

    expect(screen.getAllByText(/分析失败/)[0]).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('should display empty state when no content', () => {
    render(<Step1DeepAnalysis content="" />);

    expect(screen.getByText(/暂无分析结果/)).toBeInTheDocument();
  });
});
