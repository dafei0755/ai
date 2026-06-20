'use client';

import { useCallback, useState, type RefObject } from 'react';

const CONTEXT_PANE_MIN_PERCENT = 24;
const CONTEXT_PANE_MAX_PERCENT = 72;
const CONTEXT_PANE_DEFAULT_PERCENT = 42;

export interface UseConversationLayoutStateParams {
  sessionId: string;
  splitPaneRef: RefObject<HTMLDivElement | null>;
}

export function useConversationLayoutState({
  sessionId,
  splitPaneRef,
}: UseConversationLayoutStateParams) {
  const [briefExpanded, setBriefExpanded] = useState(false);
  const [briefPinnedOpen, setBriefPinnedOpen] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);
  const [contextPinnedOpen, setContextPinnedOpen] = useState(false);
  const [contextPanePercent, setContextPanePercent] = useState(() => {
    if (typeof window === 'undefined') return CONTEXT_PANE_DEFAULT_PERCENT;
    try {
      const stored = window.sessionStorage.getItem(`context_pane_percent_${sessionId}`);
      return stored ? clampContextPanePercent(parseInt(stored, 10)) : CONTEXT_PANE_DEFAULT_PERCENT;
    } catch {
      return CONTEXT_PANE_DEFAULT_PERCENT;
    }
  });
  const [isContextResizing, setIsContextResizing] = useState(false);

  const toggleBriefPinnedOpen = useCallback(() => {
    setBriefPinnedOpen((prev) => {
      const nextPinned = !prev;
      setBriefExpanded(nextPinned);
      return nextPinned;
    });
  }, []);

  const collapseBriefAfterHover = useCallback(() => {
    if (!briefPinnedOpen) setBriefExpanded(false);
  }, [briefPinnedOpen]);

  const toggleContextPinnedOpen = useCallback(() => {
    setContextPinnedOpen((prev) => {
      const nextPinned = !prev;
      setContextExpanded(nextPinned);
      return nextPinned;
    });
  }, []);

  const collapseContextAfterHover = useCallback(() => {
    if (!contextPinnedOpen) setContextExpanded(false);
  }, [contextPinnedOpen]);

  const updateContextPanePercentFromPointer = useCallback(
    (clientY: number) => {
      const pane = splitPaneRef.current;
      if (!pane) return;
      const rect = pane.getBoundingClientRect();
      const nextPercent = ((clientY - rect.top) / rect.height) * 100;
      setContextPanePercent(clampContextPanePercent(nextPercent));
    },
    [splitPaneRef],
  );

  const startContextResize = useCallback(() => {
    setIsContextResizing(true);
  }, []);

  const finishContextResize = useCallback(() => {
    setIsContextResizing(false);
    if (typeof document !== 'undefined') {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
    try {
      window.sessionStorage.setItem(`context_pane_percent_${sessionId}`, String(Math.round(contextPanePercent)));
    } catch (error) {
      console.warn('Failed to save context pane percent:', error);
    }
  }, [contextPanePercent, sessionId]);

  return {
    briefExpanded,
    setBriefExpanded,
    briefPinnedOpen,
    toggleBriefPinnedOpen,
    collapseBriefAfterHover,
    contextExpanded,
    setContextExpanded,
    contextPinnedOpen,
    toggleContextPinnedOpen,
    collapseContextAfterHover,
    contextPanePercent,
    isContextResizing,
    startContextResize,
    finishContextResize,
    updateContextPanePercentFromPointer,
  };
}

function clampContextPanePercent(value: number) {
  return Math.min(CONTEXT_PANE_MAX_PERCENT, Math.max(CONTEXT_PANE_MIN_PERCENT, value));
}
