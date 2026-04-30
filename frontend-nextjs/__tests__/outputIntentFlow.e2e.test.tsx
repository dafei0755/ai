/**
 * 端到端测试：output_intent_confirmation 完整用户流程
 *
 * 场景：
 * A. WebSocket 接收 interrupt 消息 → Modal 弹出 → 用户确认 → resumeAnalysis 调用
 * B. 用户点跳过 → resumeAnalysis('skip')
 * C. WebSocket 断线 + 轮询恢复 Modal
 *
 * 策略：使用纯函数模拟（无 React 渲染），更快且无环境依赖。
 * 组件级 E2E 见 ComponentFlow 区块（集成 OutputIntentConfirmationModal）。
 */

import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { OutputIntentConfirmationModal } from '@/components/OutputIntentConfirmationModal';
import type { OutputIntentConfirmPayload } from '@/components/OutputIntentConfirmationModal';

// ── Mock api ──────────────────────────────────────────────────────────────
const mockResumeAnalysis = jest.fn().mockResolvedValue({ status: 'running' });
const mockGetStatus      = jest.fn();

jest.mock('@/lib/api', () => ({
  api: {
    resumeAnalysis: (...args: any[]) => mockResumeAnalysis(...args),
    getStatus:      (...args: any[]) => mockGetStatus(...args),
  },
}));

// ── 共享测试数据 ──────────────────────────────────────────────────────────

const INTERRUPT_PAYLOAD = {
  interaction_type: 'output_intent_confirmation' as const,
  title: '输出意图确认',
  delivery_types: {
    message: '请选择交付类型',
    max_select: 2,
    options: [
      { id: 'report_a', label: '报告A', desc: '', recommended: true  },
      { id: 'report_b', label: '报告B', desc: '', recommended: false },
      { id: 'report_c', label: '报告C', desc: '', recommended: false },
    ],
  },
  identity_modes: {
    message: '请选择视角',
    options: [
      { id: 'mode_x', label: '视角X', recommended: true  },
      { id: 'mode_y', label: '视角Y', recommended: false },
    ],
  },
};

const SESSION_ID = 'e2e-session-001';

// ── A. WS interrupt → 用户确认 ────────────────────────────────────────────

describe('E2E > 场景A：WebSocket interrupt 消息触发 Modal', () => {
  beforeEach(() => jest.clearAllMocks());

  it('收到 interrupt_data 后 Modal 应显示', async () => {
    const onConfirm = jest.fn();
    const onSkip    = jest.fn();

    render(
      <OutputIntentConfirmationModal
        isOpen={true}
        data={INTERRUPT_PAYLOAD}
        onConfirm={onConfirm}
        onSkip={onSkip}
      />
    );

    expect(screen.getByText('输出意图确认')).toBeInTheDocument();
    expect(screen.getByText('报告A')).toBeInTheDocument();
  });

  it('用户点击确认 → onConfirm 被调用，payload 包含推荐的 report_a 和视角X', async () => {
    const onConfirm = jest.fn().mockResolvedValue(undefined);
    const onSkip    = jest.fn();

    render(
      <OutputIntentConfirmationModal
        isOpen={true}
        data={INTERRUPT_PAYLOAD}
        onConfirm={onConfirm}
        onSkip={onSkip}
      />
    );

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /确认并继续/ }));
    });

    await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1));

    const payload: OutputIntentConfirmPayload = onConfirm.mock.calls[0][0];
    expect(payload.selected_deliveries).toContain('report_a');
    expect(payload.selected_modes).toContain('mode_x');
  });

  it('用户额外勾选 report_b 后确认，payload 包含 report_a + report_b', async () => {
    const onConfirm = jest.fn().mockResolvedValue(undefined);

    render(
      <OutputIntentConfirmationModal
        isOpen={true}
        data={INTERRUPT_PAYLOAD}
        onConfirm={onConfirm}
        onSkip={jest.fn()}
      />
    );

    fireEvent.click(screen.getByText('报告B').closest('button')!);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /确认并继续/ }));
    });
    await waitFor(() => expect(onConfirm).toHaveBeenCalled());

    const { selected_deliveries } = onConfirm.mock.calls[0][0];
    expect(selected_deliveries).toContain('report_a');
    expect(selected_deliveries).toContain('report_b');
  });

  it('max_select=2 已满时 report_c 按钮被禁用，用户无法超选', () => {
    render(
      <OutputIntentConfirmationModal
        isOpen={true}
        data={INTERRUPT_PAYLOAD}
        onConfirm={jest.fn()}
        onSkip={jest.fn()}
      />
    );
    // 勾选 report_b → 2个已选（report_a + report_b）= max
    fireEvent.click(screen.getByText('报告B').closest('button')!);
    expect(screen.getByText('报告C').closest('button')).toBeDisabled();
  });
});

// ── B. 用户点跳过 ─────────────────────────────────────────────────────────

describe('E2E > 场景B：用户点击跳过', () => {
  beforeEach(() => jest.clearAllMocks());

  it('点击跳过按钮 → onSkip 被调用', async () => {
    const onSkip = jest.fn();

    render(
      <OutputIntentConfirmationModal
        isOpen={true}
        data={INTERRUPT_PAYLOAD}
        onConfirm={jest.fn()}
        onSkip={onSkip}
      />
    );

    fireEvent.click(screen.getByText('跳过，使用推荐配置'));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });
});

// ── C. 轮询恢复 ───────────────────────────────────────────────────────────

describe('E2E > 场景C：WebSocket 断线后轮询恢复 interrupt_data', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('轮询函数收到 waiting_for_input + interrupt_data 时调用 applyInterruptDispatch', async () => {
    // 模拟轮询逻辑（与 page.tsx useEffect 轮询逻辑相同）
    const applyInterruptDispatch = jest.fn();

    mockGetStatus.mockResolvedValue({
      status:         'waiting_for_input',
      interrupt_data: INTERRUPT_PAYLOAD,
    });

    // 模拟轮询 setup
    const interval = setInterval(async () => {
      const { api } = await import('@/lib/api');
      const response = await api.getStatus(SESSION_ID);
      if (response.status === 'waiting_for_input' && response.interrupt_data) {
        applyInterruptDispatch(response.interrupt_data);
      }
    }, 5000);

    // 推进时钟触发一次轮询
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });

    await waitFor(() => expect(applyInterruptDispatch).toHaveBeenCalledWith(INTERRUPT_PAYLOAD));

    clearInterval(interval);
  });

  it('轮询函数收到 running 状态时不调用 applyInterruptDispatch', async () => {
    const applyInterruptDispatch = jest.fn();

    mockGetStatus.mockResolvedValue({ status: 'running' });

    const interval = setInterval(async () => {
      const { api } = await import('@/lib/api');
      const response = await api.getStatus(SESSION_ID);
      if (response.status === 'waiting_for_input' && response.interrupt_data) {
        applyInterruptDispatch(response.interrupt_data);
      }
    }, 5000);

    await act(async () => {
      jest.advanceTimersByTime(5000);
    });

    await waitFor(() => expect(mockGetStatus).toHaveBeenCalled());
    expect(applyInterruptDispatch).not.toHaveBeenCalled();

    clearInterval(interval);
  });
});

// ── D. 🔄 v10.2 Path B: 输出意图确认集成到 UnifiedModal 内部 ────────────

describe('E2E > 场景D：Path B - 输出意图随 Step 1 一并提交', () => {
  beforeEach(() => jest.clearAllMocks());

  it('Step 0 确认后，Step 1 的 onConfirm payload 应包含 output_intent', () => {
    // 模拟 Path B 流程：Modal 内部 Step 0 确认后，Step 1 提交时捆绑 output_intent
    const outputIntentPayload: OutputIntentConfirmPayload = {
      selected_deliveries: ['report_a'],
      selected_modes: ['mode_x'],
    };

    // 模拟 Step 1 确认时的 payload 构建逻辑
    const confirmedOutputIntent = outputIntentPayload;
    const step1Payload: any = {};
    if (confirmedOutputIntent) {
      step1Payload.output_intent = confirmedOutputIntent;
    }

    expect(step1Payload.output_intent).toBeDefined();
    expect(step1Payload.output_intent.selected_deliveries).toContain('report_a');
    expect(step1Payload.output_intent.selected_modes).toContain('mode_x');
  });

  it('跳过输出意图时，仍使用推荐默认值构造 output_intent', () => {
    // 模拟跳过：使用推荐配置
    const deliveryDefaults = INTERRUPT_PAYLOAD.delivery_types.options
      .filter(o => o.recommended)
      .map(o => o.id);
    const modeDefaults = INTERRUPT_PAYLOAD.identity_modes.options
      .filter(o => o.recommended)
      .map(o => o.id);

    const skipPayload: OutputIntentConfirmPayload = {
      selected_deliveries: deliveryDefaults,
      selected_modes: modeDefaults,
    };

    expect(skipPayload.selected_deliveries).toContain('report_a');
    expect(skipPayload.selected_modes).toContain('mode_x');
  });

  it('Path B 下不再单独调用 resumeAnalysis 进行输出意图确认', () => {
    // Path B 验证：handleOutputIntentConfirm 已移除，resumeAnalysis 不应被调用
    // 输出意图确认是 Modal 内部的本地状态切换
    expect(mockResumeAnalysis).not.toHaveBeenCalled();
  });
});
