import { existsSync } from 'fs';
import path from 'path';

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

const composerShellPath = path.join(__dirname, 'ComposerShell.tsx');

const loadComposerShell = () => {
  expect(existsSync(composerShellPath)).toBe(true);

  const { ComposerShell } = require('./ComposerShell') as typeof import('./ComposerShell');
  return ComposerShell;
};

describe('conversation composer shell', () => {
  it('renders textarea content, updates text, and sends when enabled', async () => {
    const user = userEvent.setup();
    const handleSend = jest.fn();
    const handleKeyDown = jest.fn();
    const ComposerShell = loadComposerShell();
    const Harness = () => {
      const [inputText, setInputText] = React.useState('返乡民居');
      const textareaRef = React.useRef<HTMLTextAreaElement>(null);

      return (
        <ComposerShell
          textareaRef={textareaRef}
          inputText={inputText}
          setInputText={setInputText}
          handleKeyDown={handleKeyDown}
          handleSend={handleSend}
          placeholder="输入需求"
          loading={false}
        />
      );
    };

    render(<Harness />);

    const textbox = screen.getByRole('textbox');
    expect(textbox).toHaveValue('返乡民居');

    await user.clear(textbox);
    await user.type(textbox, '身心安放');
    await user.click(screen.getByRole('button', { name: '发送' }));

    expect(textbox).toHaveValue('身心安放');
    expect(handleSend).toHaveBeenCalledTimes(1);
  });

  it('disables sending while empty or loading', () => {
    const ComposerShell = loadComposerShell();
    const noopRef = { current: null } as React.RefObject<HTMLTextAreaElement | null>;
    const props = {
      textareaRef: noopRef,
      setInputText: jest.fn(),
      handleKeyDown: jest.fn(),
      handleSend: jest.fn(),
      placeholder: '输入需求',
    };

    const { rerender } = render(
      <ComposerShell
        {...props}
        inputText="   "
        loading={false}
      />,
    );

    expect(screen.getByRole('button', { name: '发送' })).toBeDisabled();

    rerender(
      <ComposerShell
        {...props}
        inputText="可以发送"
        loading
      />,
    );

    expect(screen.getByRole('button', { name: '发送' })).toBeDisabled();
  });

  it('keeps the restored rounded floating input shell', () => {
    const source = require('fs').readFileSync(composerShellPath, 'utf8') as string;

    expect(source).toContain('advisor-composer-shell rounded-[1.6rem] border border-[var(--border-color)] shadow-lg');
    expect(source).toContain('advisor-chat-column mx-auto w-full pointer-events-auto');
    expect(source).not.toContain('ui-card-shell ui-card-shell-strong rounded-[1.6rem]');
    expect(source).not.toContain('max-w-[960px]');
  });
});
