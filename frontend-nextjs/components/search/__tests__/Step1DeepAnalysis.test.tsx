import { render, screen } from '@testing-library/react';
import Step1DeepAnalysis from '../Step1DeepAnalysis';

describe('Step1DeepAnalysis', () => {
  const mockV2Output = `
**【您将获得什么】**

📦 您的定制民宿设计方案包含：

✅ 4个核心板块，共计约15页内容
✅ 预计包含20+个实际案例参考

📋 具体内容：

1️⃣ **HAY美学应用策略**（约4页）
   • HAY品牌5个核心设计元素解析

---

**【我们如何理解您的需求】**

🎯 我们理解您的核心需求：

**您想要的效果：**
• 融入HAY设计美学

---

**【接下来的搜索计划】**

🔍 我们将为您搜索：

**第一优先级（核心信息）：**
✓ HAY品牌官方案例库
`;

  it('should render v2.0 format with three sections', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getByText(/您将获得什么/)).toBeInTheDocument();
    expect(screen.getByText(/我们如何理解您的需求/)).toBeInTheDocument();
    expect(screen.getByText(/接下来的搜索计划/)).toBeInTheDocument();
  });

  it('should display deliverables section with visual markers', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getAllByText(/📦/)[0]).toBeInTheDocument();
    expect(screen.getByText(/4个核心板块/)).toBeInTheDocument();
    expect(screen.getByText(/20\+个实际案例参考/)).toBeInTheDocument();
  });

  it('should display blocks with numbered emojis', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getByText(/1️⃣/)).toBeInTheDocument();
    expect(screen.getByText(/HAY美学应用策略/)).toBeInTheDocument();
  });

  it('should display understanding section with target emoji', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getAllByText(/🎯/)[0]).toBeInTheDocument();
    expect(screen.getByText(/您想要的效果/)).toBeInTheDocument();
  });

  it('should display search plan with magnifying glass emoji', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getAllByText(/🔍/)[0]).toBeInTheDocument();
    expect(screen.getByText(/第一优先级/)).toBeInTheDocument();
  });

  it('should have proper ARIA labels', () => {
    render(<Step1DeepAnalysis content={mockV2Output} />);

    expect(screen.getByRole('region', { name: /您将获得什么/ })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /我们如何理解您的需求/ })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /接下来的搜索计划/ })).toBeInTheDocument();
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
