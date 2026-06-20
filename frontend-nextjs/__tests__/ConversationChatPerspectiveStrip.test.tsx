import { render, screen } from '@testing-library/react';
import ConversationChat from '@/components/ConversationMode/ConversationChat';

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock('remark-gfm', () => jest.fn());
jest.mock('rehype-raw', () => jest.fn());
jest.mock('rehype-sanitize', () => jest.fn());

describe('ConversationChat perspective strip', () => {
  it('does not expose the internal perspective selector above the composer', () => {
    render(
      <ConversationChat
        sessionId="test-session"
        messages={[]}
        onSendMessage={jest.fn()}
      />
    );

    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /召集/ })).not.toBeInTheDocument();
  });
});
