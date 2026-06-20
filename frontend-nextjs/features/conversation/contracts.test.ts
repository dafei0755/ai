import { existsSync, readFileSync } from 'fs';
import path from 'path';

import { CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT } from './contracts';
import type { ChatMessage, GuidanceCardData, GuidanceCardStructuredResponse } from './types';

const repoRoot = path.resolve(__dirname, '../../..');
const readRepoFile = (relativePath: string) =>
  readFileSync(path.join(repoRoot, relativePath), 'utf8');

describe('conversation-analysis-ui module contract', () => {
  it('registers the governed frontend feature boundary', () => {
    expect(CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT).toMatchObject({
      moduleId: 'conversation-analysis-ui',
      currentVersion: 'v0.4-composer-hook-extracted',
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
    const conversationTypesSource = readRepoFile('frontend-nextjs/features/conversation/types.ts');

    for (const cardType of CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT.requiredGuidanceCardTypes) {
      expect(conversationTypesSource).toContain(`'${cardType}'`);
    }
    expect(conversationChatSource).toContain("from '@/features/conversation/types'");
  });

  it('keeps the critical user-facing interaction tests attached to the module', () => {
    const guidanceCardTestSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/GuidanceCard.test.tsx',
    );
    const conversationChatTestSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.test.tsx',
    );
    const composerHookTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/hooks/useConversationComposer.test.ts',
    );
    const contractTestSource = readRepoFile('frontend-nextjs/features/conversation/contracts.test.ts');
    const combinedTestSource = `${guidanceCardTestSource}\n${conversationChatTestSource}\n${composerHookTestSource}\n${contractTestSource}`;

    for (const testCaseName of CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT.protectedTestCases) {
      expect(combinedTestSource).toContain(testCaseName);
    }
  });

  it('keeps conversation data types in the feature layer', () => {
    const message: ChatMessage = {
      id: 'contract-message',
      role: 'assistant',
      content: 'contract',
      timestamp: '2026-06-20T00:00:00.000Z',
    };
    const card: GuidanceCardData = {
      card_id: 'contract-card',
      card_type: 'demand_reconstruction_blueprint',
      prompt_text: 'contract',
      options: [],
    };
    const response: GuidanceCardStructuredResponse = { pages: [] };

    expect(message.role).toBe('assistant');
    expect(card.card_type).toBe('demand_reconstruction_blueprint');
    expect(response.pages).toEqual([]);
  });

  it('keeps message card rendering in the feature layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const rendererSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/MessageCardRenderer.tsx',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/components/MessageCardRenderer'");
    expect(conversationChatSource).not.toContain('function SchemeVersionSelectionCard');
    expect(rendererSource).toContain('export function MessageCardRenderer');
    expect(rendererSource).toContain('scheme_version_selection');
    expect(rendererSource).toContain('CandidateCard');
    expect(rendererSource).toContain('GuidanceCardWidget');
  });

  it('keeps conversation composer behavior in the feature hook layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const composerHookSource = readRepoFile(
      'frontend-nextjs/features/conversation/hooks/useConversationComposer.ts',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/hooks/useConversationComposer'");
    expect(composerHookSource).toContain('export function useConversationComposer');
    expect(composerHookSource).toContain('handleSend');
    expect(composerHookSource).toContain('handleAdvisorPrompt');
    expect(composerHookSource).toContain('prefillHint');
  });
});
