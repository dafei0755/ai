import { existsSync } from 'fs';
import path from 'path';

import { render, screen } from '@testing-library/react';
import type React from 'react';

import type { ChatMessage } from '@/features/conversation/types';

const messageListShellPath = path.join(__dirname, 'MessageListShell.tsx');

jest.mock('./MessageCardRenderer', () => ({
  MessageCardRenderer: ({ message }: { message: ChatMessage }) => (
    <article data-testid="message-card-renderer">{message.content}</article>
  ),
}));

const loadMessageListShell = () => {
  expect(existsSync(messageListShellPath)).toBe(true);

  const { MessageListShell } = require('./MessageListShell') as typeof import('./MessageListShell');
  return MessageListShell;
};

describe('conversation message list shell', () => {
  it('renders the empty conversation state', () => {
    const MessageListShell = loadMessageListShell();

    render(
      <MessageListShell
        scrollRef={{ current: null } as React.RefObject<HTMLDivElement | null>}
        visibleMessages={[]}
        loading={false}
        adaptiveChatGutter="12px"
      />,
    );

    expect(screen.getByText('随时开始聊')).toBeInTheDocument();
    expect(screen.getByText('分享你的想法、灵感或设计需求')).toBeInTheDocument();
  });

  it('renders visible messages and typing indicator while loading', () => {
    const MessageListShell = loadMessageListShell();
    const messages: ChatMessage[] = [
      {
        id: 'assistant-1',
        role: 'assistant',
        content: '需求洞察',
        timestamp: '2026-06-20T00:00:00.000Z',
      },
    ];

    render(
      <MessageListShell
        scrollRef={{ current: null } as React.RefObject<HTMLDivElement | null>}
        visibleMessages={messages}
        loading
        adaptiveChatGutter="12px"
      />,
    );

    expect(screen.getByTestId('message-card-renderer')).toHaveTextContent('需求洞察');
    expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();
  });
});
