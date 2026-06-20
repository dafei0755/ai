'use client';

import { ArrowUp } from 'lucide-react';
import type React from 'react';

import { ExpertControls } from '@/features/conversation/components/ExpertControls';

interface ComposerShellProps {
  adaptiveChatGutter?: string;
  activeExpertPerspective?: string;
  expertPerspectiveOptions?: readonly string[];
  onExpertPerspectiveChange?: (next: string) => void;
  summonOptions?: readonly string[];
  onSummonExpert?: (target: string) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  inputText: string;
  setInputText: (next: string) => void;
  handleKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleSend: () => void;
  placeholder: string;
  loading: boolean;
}

export function ComposerShell({
  adaptiveChatGutter = 'clamp(12px, 2vw, 32px)',
  activeExpertPerspective = '默认综合',
  expertPerspectiveOptions = [],
  onExpertPerspectiveChange,
  summonOptions = [],
  onSummonExpert,
  textareaRef,
  inputText,
  setInputText,
  handleKeyDown,
  handleSend,
  placeholder,
  loading,
}: ComposerShellProps) {
  const canSend = Boolean(inputText.trim()) && !loading;

  return (
    <div
      className="absolute bottom-0 left-0 right-0 pb-4 pt-8 bg-gradient-to-t from-[var(--background)] via-[var(--background)] to-transparent pointer-events-none"
      style={{ paddingInline: adaptiveChatGutter }}
    >
      <div className="mx-auto w-full max-w-[960px] pointer-events-auto">
        <ExpertControls
          activeExpertPerspective={activeExpertPerspective}
          expertPerspectiveOptions={expertPerspectiveOptions}
          onExpertPerspectiveChange={onExpertPerspectiveChange}
          summonOptions={summonOptions}
          onSummonExpert={onSummonExpert}
        />
        <div className="ui-card-shell ui-card-shell-strong rounded-[1.6rem] overflow-hidden bg-[var(--card-bg)]">
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={(event) => setInputText(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={2}
            className="ui-type-body w-full bg-transparent text-[var(--foreground)] px-5 pt-4 pb-2 outline-none resize-none max-h-32 overflow-y-auto placeholder:text-[var(--foreground-secondary)]"
            style={{ fieldSizing: 'content' } as React.CSSProperties}
          />
          <div className="flex items-center justify-end px-4 pb-3">
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={`p-2 rounded-full transition-all duration-300 ${
                canSend
                  ? 'bg-[var(--foreground)] text-[var(--background)] hover:opacity-80 hover:scale-105'
                  : 'bg-[var(--border-color)] text-[var(--foreground-secondary)] cursor-not-allowed opacity-50'
              }`}
              aria-label="发送"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
