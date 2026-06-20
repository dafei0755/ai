import { act, renderHook } from '@testing-library/react';

import { useConversationLayoutState } from './useConversationLayoutState';

describe('useConversationLayoutState', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('restores context pane percent, clamps drag updates, and persists on resize end', () => {
    window.sessionStorage.setItem('context_pane_percent_session-a', '68');
    const pane = {
      getBoundingClientRect: () => ({ top: 100, height: 200 }) as DOMRect,
    } as HTMLDivElement;
    const splitPaneRef = { current: pane };

    const { result } = renderHook(() =>
      useConversationLayoutState({
        sessionId: 'session-a',
        splitPaneRef,
      }),
    );

    expect(result.current.contextPanePercent).toBe(68);

    act(() => result.current.startContextResize());
    act(() => result.current.updateContextPanePercentFromPointer(1000));
    expect(result.current.contextPanePercent).toBe(72);

    act(() => result.current.updateContextPanePercentFromPointer(0));
    expect(result.current.contextPanePercent).toBe(24);

    act(() => result.current.finishContextResize());
    expect(result.current.isContextResizing).toBe(false);
    expect(window.sessionStorage.getItem('context_pane_percent_session-a')).toBe('24');
  });

  it('keeps hover collapse disabled while panels are pinned open', () => {
    const { result } = renderHook(() =>
      useConversationLayoutState({
        sessionId: 'session-b',
        splitPaneRef: { current: null },
      }),
    );

    act(() => result.current.toggleBriefPinnedOpen());
    expect(result.current.briefPinnedOpen).toBe(true);
    expect(result.current.briefExpanded).toBe(true);

    act(() => result.current.collapseBriefAfterHover());
    expect(result.current.briefExpanded).toBe(true);

    act(() => result.current.toggleContextPinnedOpen());
    expect(result.current.contextPinnedOpen).toBe(true);
    expect(result.current.contextExpanded).toBe(true);

    act(() => result.current.collapseContextAfterHover());
    expect(result.current.contextExpanded).toBe(true);
  });
});
