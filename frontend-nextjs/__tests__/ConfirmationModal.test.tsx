import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConfirmationModal } from '@/components/ConfirmationModal';

describe('ConfirmationModal', () => {
  const mockOnConfirm = jest.fn();
  const mockOnEdit = jest.fn();

  const defaultProps = {
    isOpen: true,
    title: '需求确认',
    message: '请确认您的项目需求是否正确',
    onConfirm: mockOnConfirm,
    onEdit: mockOnEdit,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should not render when isOpen is false', () => {
    const { container } = render(
      <ConfirmationModal {...defaultProps} isOpen={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('should render modal with title and message', () => {
    render(<ConfirmationModal {...defaultProps} />);

    expect(screen.getByText('需求确认')).toBeInTheDocument();
    expect(screen.getByText('请确认您的项目需求是否正确')).toBeInTheDocument();
  });

  it('should render summary items from array', () => {
    const summary = [
      { label: '项目类型', content: '咖啡馆设计' },
      { label: '预算范围', content: '50-100万' },
    ];

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    expect(screen.getByText('项目类型')).toBeInTheDocument();
    expect(screen.getByText('咖啡馆设计')).toBeInTheDocument();
    expect(screen.getByText('预算范围')).toBeInTheDocument();
    expect(screen.getByText('50-100万')).toBeInTheDocument();
  });

  it('should call onConfirm when clicking confirm button', () => {
    render(<ConfirmationModal {...defaultProps} />);

    const confirmButton = screen.getByText('确认继续');
    fireEvent.click(confirmButton);

    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('should enter edit mode when clicking edit button', () => {
    const summary = [{ label: '项目类型', content: '咖啡馆设计' }];

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    const editButton = screen.getByText('修改需求');
    fireEvent.click(editButton);

    // Should show editing UI
    expect(screen.getByPlaceholderText('输入标题...')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('输入详细内容...')).toBeInTheDocument();
    expect(screen.getByText('保存并继续')).toBeInTheDocument();
    expect(screen.getByText('取消')).toBeInTheDocument();
  });

  it('should allow editing item content', () => {
    const summary = [{ label: '项目类型', content: '咖啡馆设计' }];

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    // Enter edit mode
    fireEvent.click(screen.getByText('修改需求'));

    // Edit label
    const labelInput = screen.getByPlaceholderText('输入标题...') as HTMLInputElement;
    fireEvent.change(labelInput, { target: { value: '项目名称' } });
    expect(labelInput.value).toBe('项目名称');

    // Edit content
    const contentInput = screen.getByPlaceholderText('输入详细内容...') as HTMLTextAreaElement;
    fireEvent.change(contentInput, { target: { value: '精品咖啡馆设计' } });
    expect(contentInput.value).toBe('精品咖啡馆设计');
  });

  it('should save edited data when confirming in edit mode', () => {
    const summary = [{ label: '项目类型', content: '咖啡馆设计' }];

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    // Enter edit mode
    fireEvent.click(screen.getByText('修改需求'));

    // Edit content
    const contentInput = screen.getByPlaceholderText('输入详细内容...') as HTMLTextAreaElement;
    fireEvent.change(contentInput, { target: { value: '精品咖啡馆设计' } });

    // Save
    fireEvent.click(screen.getByText('保存并继续'));

    // Should call onConfirm with edited data
    expect(mockOnConfirm).toHaveBeenCalledWith([
      { label: '项目类型', content: '精品咖啡馆设计' },
    ]);
  });

  it('should cancel editing and restore original data', () => {
    const summary = [{ label: '项目类型', content: '咖啡馆设计' }];

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    // Enter edit mode
    fireEvent.click(screen.getByText('修改需求'));

    // Edit content
    const contentInput = screen.getByPlaceholderText('输入详细内容...') as HTMLTextAreaElement;
    fireEvent.change(contentInput, { target: { value: '修改后的内容' } });

    // Cancel
    fireEvent.click(screen.getByText('取消'));

    // Should exit edit mode and restore original data
    expect(screen.queryByPlaceholderText('输入标题...')).not.toBeInTheDocument();
    expect(screen.getByText('咖啡馆设计')).toBeInTheDocument();
  });

  it('should handle object summary by extracting array', () => {
    const summary = {
      requirements: [{ label: '需求1', content: '内容1' }],
    };

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    expect(screen.getByText('需求1')).toBeInTheDocument();
    expect(screen.getByText('内容1')).toBeInTheDocument();
  });

  it('should handle non-array object summary', () => {
    const summary = { label: '单个需求', content: '需求内容' };

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    expect(screen.getByText('单个需求')).toBeInTheDocument();
    expect(screen.getByText('需求内容')).toBeInTheDocument();
  });

  it('should show item numbers for multiple items', () => {
    const summary = [
      { label: '需求1', content: '内容1' },
      { label: '需求2', content: '内容2' },
      { label: '需求3', content: '内容3' },
    ];

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('should show editing hint in edit mode', () => {
    const summary = [{ label: '项目类型', content: '咖啡馆设计' }];

    render(<ConfirmationModal {...defaultProps} summary={summary} />);

    // Should not show hint initially
    expect(screen.queryByText(/编辑模式/)).not.toBeInTheDocument();

    // Enter edit mode
    fireEvent.click(screen.getByText('修改需求'));

    // Should show hint
    expect(screen.getByText(/编辑模式/)).toBeInTheDocument();
  });

  it('should apply correct styling classes', () => {
    render(<ConfirmationModal {...defaultProps} />);

    // Check backdrop
    const backdrop = document.querySelector('.fixed.inset-0.bg-black\\/50');
    expect(backdrop).toBeInTheDocument();

    // Check modal container
    const modal = document.querySelector('.bg-white.dark\\:bg-\\[var\\(--card-bg\\)\\]');
    expect(modal).toBeInTheDocument();
  });
});
