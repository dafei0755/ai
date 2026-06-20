import { act, renderHook } from '@testing-library/react';

import { useConversationComposer } from './useConversationComposer';

describe('useConversationComposer', () => {
  it('trims sends, clears the composer, and restores focus', () => {
    const onSendMessage = jest.fn();
    const focus = jest.fn();
    const textareaRef = { current: { focus } as unknown as HTMLTextAreaElement };

    const { result } = renderHook(() =>
      useConversationComposer({
        loading: false,
        onSendMessage,
        textareaRef,
      }),
    );

    act(() => result.current.setInputText('  返乡民居需求  '));
    act(() => result.current.handleSend());

    expect(onSendMessage).toHaveBeenCalledWith('返乡民居需求');
    expect(result.current.inputText).toBe('');
    expect(focus).toHaveBeenCalledTimes(1);
  });

  it('ignores empty and loading sends', () => {
    const onSendMessage = jest.fn();
    const textareaRef = { current: null };

    const empty = renderHook(() =>
      useConversationComposer({
        loading: false,
        onSendMessage,
        textareaRef,
      }),
    );
    act(() => empty.result.current.setInputText('   '));
    act(() => empty.result.current.handleSend());

    const loading = renderHook(() =>
      useConversationComposer({
        loading: true,
        onSendMessage,
        textareaRef,
      }),
    );
    act(() => loading.result.current.setInputText('不要发送'));
    act(() => loading.result.current.handleSend());

    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it('injects prefill once and builds advisor scene prompts', () => {
    const onSendMessage = jest.fn();
    const focus = jest.fn();
    const textareaRef = { current: { focus } as unknown as HTMLTextAreaElement };
    const { result, rerender } = renderHook(
      ({ prefillId }) =>
        useConversationComposer({
          loading: false,
          onSendMessage,
          textareaRef,
          prefillHint: { id: prefillId, text: '@用户需求' },
          advisorSceneContext: {
            key: 'scene-key',
            label: '项目底盘',
            sceneRef: '场景/project/files',
            suggestion: '建议',
          },
        }),
      { initialProps: { prefillId: 1 } },
    );

    expect(result.current.inputText).toBe('@用户需求');

    rerender({ prefillId: 2 });
    expect(result.current.inputText).toBe('@用户需求');

    act(() => result.current.handleAdvisorPrompt('action-list'));
    expect(result.current.inputText).toContain('@场景/project/files');
    expect(result.current.inputText).toContain('行动清单');
  });
});
