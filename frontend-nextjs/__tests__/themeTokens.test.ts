import { readFileSync } from 'fs';
import path from 'path';

const globalsCss = readFileSync(path.join(process.cwd(), 'app', 'globals.css'), 'utf8');
const activeShellSources = [
  'app/page.tsx',
  'components/layout/AppSessionShell.tsx',
  'app/search/[session_id]/page.tsx',
].map((filePath) => readFileSync(path.join(process.cwd(), filePath), 'utf8'));
const homePageSource = readFileSync(path.join(process.cwd(), 'app', 'page.tsx'), 'utf8');
const conversationChatSource = readFileSync(
  path.join(process.cwd(), 'components', 'ConversationMode', 'ConversationChat.tsx'),
  'utf8',
);
const externalReferenceNamePattern = new RegExp(['deep', 'seek'].join(''), 'i');

describe('global dark theme tokens', () => {
  it('uses a dark gray background and text contrast tokens by default', () => {
    expect(globalsCss).toContain('--background: #151517;');
    expect(globalsCss).toContain('--sidebar-bg: #1B1B1C;');
    expect(globalsCss).toContain('--card-bg: #2C2C2E;');
    expect(globalsCss).toContain('--foreground: #f5f5f5;');
    expect(globalsCss).toContain('--foreground-secondary: #b4b4b4;');
    expect(globalsCss).toContain('--border-color: #2a2a2a;');
    expect(globalsCss).not.toContain('--background: #000000;');
    expect(globalsCss).not.toContain('--sidebar-bg: #000000;');
  });

  it('provides an advisor chat shell override that is independent of saved light theme', () => {
    expect(globalsCss).toContain('.ucppt-advisor-shell');
    expect(globalsCss).toContain('--background: #151517;');
    expect(globalsCss).toContain('--sidebar-bg: #1B1B1C;');
    expect(globalsCss).toContain('--card-bg: #2C2C2E;');
    expect(globalsCss).toContain('--foreground: #f5f5f5;');
  });

  it('uses theme tokens for the home composer instead of a forced white panel', () => {
    expect(homePageSource).not.toContain('强制白色背景');
    expect(homePageSource).not.toContain('overflow-hidden bg-white');
    expect(homePageSource).not.toContain('rounded-b-xl bg-gray-50');
    expect(homePageSource).toContain('bg-[var(--card-bg)]');
  });

  it('keeps the home composer and conversation composer at the same width', () => {
    expect(globalsCss).toContain('--advisor-chat-column-width: 960px;');
    expect(homePageSource).toContain('max-w-[var(--advisor-chat-column-width)]');
    expect(conversationChatSource).toContain('max-w-[var(--advisor-chat-column-width)]');
    expect(homePageSource).toContain('w-[calc(100%-clamp(24px,4vw,64px))]');
    expect(homePageSource).not.toContain('max-w-3xl');
    expect(homePageSource).not.toContain('px-4 sm:px-8');
  });

  it('aligns the home composer itself to the page center line', () => {
    expect(homePageSource).toContain('top-1/2');
    expect(homePageSource).toContain('-translate-y-1/2');
    expect(homePageSource).not.toContain('pt-[174px]');
  });

  it('keeps the home title one line higher above the centered composer', () => {
    expect(homePageSource).toContain('-translate-y-[calc(100%+10.25rem)]');
    expect(homePageSource).not.toContain('-translate-y-[calc(100%+8rem)]');
  });

  it('does not encode external reference product names in active shell sources', () => {
    expect([globalsCss, ...activeShellSources].join('\n')).not.toMatch(externalReferenceNamePattern);
  });
});
