import { existsSync, readFileSync } from 'fs';
import path from 'path';

import { CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT } from './contracts';

const repoRoot = path.resolve(process.cwd(), '..');
const readRepoFile = (relativePath: string) =>
  readFileSync(path.join(repoRoot, relativePath), 'utf8');

describe('conversation-analysis-ui module contract', () => {
  it('registers the governed frontend feature boundary', () => {
    expect(CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT).toMatchObject({
      moduleId: 'conversation-analysis-ui',
      currentVersion: 'v0.1-feature-boundary-contract',
    });

    for (const ownedPath of CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT.ownedPaths) {
      if (ownedPath.endsWith('/')) continue;
      expect(existsSync(path.join(repoRoot, ownedPath))).toBe(true);
    }
  });

  it('keeps required guidance card types in the conversation source contract', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const guidanceCardSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/GuidanceCard.tsx',
    );

    for (const cardType of CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT.requiredGuidanceCardTypes) {
      expect(conversationChatSource).toContain(`'${cardType}'`);
      expect(guidanceCardSource).toContain(cardType);
    }
  });

  it('keeps the critical user-facing interaction tests attached to the module', () => {
    const guidanceCardTestSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/GuidanceCard.test.tsx',
    );
    const conversationChatTestSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.test.tsx',
    );
    const combinedTestSource = `${guidanceCardTestSource}\n${conversationChatTestSource}`;

    for (const testCaseName of CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT.protectedTestCases) {
      expect(combinedTestSource).toContain(testCaseName);
    }
  });
});
