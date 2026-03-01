/**
 * 单元测试：OutputIntentConfirmationModal 组件
 *
 * 覆盖：
 * - 渲染（isOpen=false / isOpen=true）
 * - 交付类型多选（预选、点击、上限限制）
 * - 身份视角多选
 * - 跳过按钮
 * - 确认按钮（payload 结构、无选择时 fallback 推荐项）
 * - 提交中状态（loading）
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OutputIntentConfirmationModal } from '@/components/OutputIntentConfirmationModal';
import type { OutputIntentConfirmPayload } from '@/components/OutputIntentConfirmationModal';

const makeData = (overrides = {}) => ({
  interaction_type: 'output_intent_confirmation' as const,
  title: '输出意图确认',
  delivery_types: {
    message: '交付类型（文件给谁看）：',
    options: [
      { id: 'design_professional', label: '设计专业报告', desc: '面向设计团队', recommended: true },
      { id: 'investor_operator',   label: '投资运营分析',  desc: '面向投资方',   recommended: true },
      { id: 'government_policy',   label: '政策汇报方案',  desc: '面向政府',     recommended: false },
      { id: 'construction_exec',   label: '施工深化方案',  desc: '面向施工方',   recommended: false },
    ],
    max_select: 3,
  },
  identity_modes: {
    message: '体验视角（空间中的身份模式）：',
    options: [
      { id: 'as_cultural_witness', label: '作为文化见证者（游客身份）', recommended: false },
      { id: 'as_operator',         label: '作为运营者',                recommended: true  },
    ],
  },
  ...overrides,
});

describe('单元测试 > OutputIntentConfirmationModal', () => {
  const onConfirm = jest.fn();
  const onSkip    = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── 渲染 ─────────────────────────────────────────────────────────────────
  describe('渲染', () => {
    it('isOpen=false 时不渲染任何内容', () => {
      const { container } = render(
        <OutputIntentConfirmationModal isOpen={false} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('data=null 时不渲染任何内容', () => {
      const { container } = render(
        <OutputIntentConfirmationModal isOpen={true} data={null} onConfirm={onConfirm} onSkip={onSkip} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('标题、交付类型消息、身份视角消息均正确渲染', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      expect(screen.getByText('输出意图确认')).toBeInTheDocument();
      expect(screen.getByText('交付类型（文件给谁看）：')).toBeInTheDocument();
      expect(screen.getByText('体验视角（空间中的身份模式）：')).toBeInTheDocument();
    });

    it('渲染所有交付类型选项', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      expect(screen.getByText('设计专业报告')).toBeInTheDocument();
      expect(screen.getByText('投资运营分析')).toBeInTheDocument();
      expect(screen.getByText('政策汇报方案')).toBeInTheDocument();
      expect(screen.getByText('施工深化方案')).toBeInTheDocument();
    });

    it('渲染所有身份视角选项', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      expect(screen.getByText('作为文化见证者（游客身份）')).toBeInTheDocument();
      expect(screen.getByText('作为运营者')).toBeInTheDocument();
    });

    it('recommended=true 的选项显示"推荐"标签', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      // 有两个交付推荐 + 一个身份推荐 = 3 个 "推荐" 标签
      const badges = screen.getAllByText('推荐');
      expect(badges.length).toBeGreaterThanOrEqual(2);
    });

    it('没有 identity_modes 时不渲染身份视角区域', () => {
      const data = makeData({ identity_modes: undefined });
      render(
        <OutputIntentConfirmationModal isOpen={true} data={data} onConfirm={onConfirm} onSkip={onSkip} />
      );
      expect(screen.queryByText('体验视角（空间中的身份模式）：')).not.toBeInTheDocument();
    });
  });

  // ── 默认预选 ──────────────────────────────────────────────────────────────
  describe('默认预选逻辑', () => {
    it('初始时 recommended=true 的交付类型已选中（确认按钮可点击）', async () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      const confirmBtn = screen.getByRole('button', { name: /确认并继续/ });
      expect(confirmBtn).not.toBeDisabled();
    });

    it('没有任何 recommended 时确认按钮禁用', () => {
      const data = makeData();
      data.delivery_types.options.forEach((o) => { (o as any).recommended = false; });
      render(
        <OutputIntentConfirmationModal isOpen={true} data={data} onConfirm={onConfirm} onSkip={onSkip} />
      );
      const confirmBtn = screen.getByRole('button', { name: /确认并继续/ });
      expect(confirmBtn).toBeDisabled();
    });
  });

  // ── 交付类型多选逻辑 ───────────────────────────────────────────────────────
  describe('交付类型多选', () => {
    it('点击未选中选项可将其加入选择集', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      // 政策汇报方案初始未选，点击后应可提交（已有2个+1=3，未超限）
      const govOption = screen.getByText('政策汇报方案').closest('button')!;
      fireEvent.click(govOption);
      // 按钮仍可点击（3=max_select）
      expect(screen.getByRole('button', { name: /确认并继续/ })).not.toBeDisabled();
    });

    it('超过 max_select 时新选项被禁用', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      // 已选 2（recommended），再选第3个到达上限
      fireEvent.click(screen.getByText('政策汇报方案').closest('button')!);
      // 此时施工深化方案应被禁用
      const constructionBtn = screen.getByText('施工深化方案').closest('button')!;
      expect(constructionBtn).toBeDisabled();
    });

    it('达到上限后显示"已达上限"提示', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      fireEvent.click(screen.getByText('政策汇报方案').closest('button')!);
      expect(screen.getByText('已达上限')).toBeInTheDocument();
    });

    it('点击已选中选项可取消选择', () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      // 取消"设计专业报告"（默认已选）
      fireEvent.click(screen.getByText('设计专业报告').closest('button')!);
      // 确认按钮仍可用（还有投资运营分析）
      expect(screen.getByRole('button', { name: /确认并继续/ })).not.toBeDisabled();
    });
  });

  // ── 提交逻辑 ──────────────────────────────────────────────────────────────
  describe('确认提交', () => {
    it('点击确认按钮调用 onConfirm，传入 selected_deliveries 和 selected_modes', async () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      fireEvent.click(screen.getByRole('button', { name: /确认并继续/ }));
      await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1));

      const payload: OutputIntentConfirmPayload = onConfirm.mock.calls[0][0];
      expect(payload).toHaveProperty('selected_deliveries');
      expect(payload).toHaveProperty('selected_modes');
      expect(Array.isArray(payload.selected_deliveries)).toBe(true);
      expect(Array.isArray(payload.selected_modes)).toBe(true);
    });

    it('payload 中 selected_deliveries 包含初始推荐项', async () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      fireEvent.click(screen.getByRole('button', { name: /确认并继续/ }));
      await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1));

      const { selected_deliveries } = onConfirm.mock.calls[0][0];
      expect(selected_deliveries).toContain('design_professional');
      expect(selected_deliveries).toContain('investor_operator');
    });

    it('手动勾选非推荐项后 payload 包含该项', async () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      fireEvent.click(screen.getByText('政策汇报方案').closest('button')!);
      fireEvent.click(screen.getByRole('button', { name: /确认并继续/ }));
      await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1));

      const { selected_deliveries } = onConfirm.mock.calls[0][0];
      expect(selected_deliveries).toContain('government_policy');
    });

    it('提交中状态禁用确认按钮并显示加载文字', async () => {
      // onConfirm 返回一个永不 resolve 的 Promise，模拟加载中
      const slowConfirm = jest.fn(() => new Promise(() => {}));
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={slowConfirm} onSkip={onSkip} />
      );
      fireEvent.click(screen.getByRole('button', { name: /确认并继续/ }));
      await waitFor(() => expect(screen.getByText('提交中...')).toBeInTheDocument());
      expect(screen.getByRole('button', { name: /提交中/ })).toBeDisabled();
    });
  });

  // ── 跳过按钮 ──────────────────────────────────────────────────────────────
  describe('跳过', () => {
    it('点击跳过按钮调用 onSkip', async () => {
      render(
        <OutputIntentConfirmationModal isOpen={true} data={makeData()} onConfirm={onConfirm} onSkip={onSkip} />
      );
      fireEvent.click(screen.getByText('跳过，使用推荐配置'));
      expect(onSkip).toHaveBeenCalledTimes(1);
    });
  });
});
