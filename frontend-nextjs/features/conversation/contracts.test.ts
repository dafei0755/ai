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
      currentVersion: 'v1.7-conversation-local-persistence-extracted',
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
    const conversationHistoryAdapterTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationHistoryAdapter.test.ts',
    );
    const conversationSessionBootstrapTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationSessionBootstrap.test.ts',
    );
    const conversationActionHandlersTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationActionHandlers.test.ts',
    );
    const conversationLocalPersistenceTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationLocalPersistence.test.ts',
    );
    const conversationChatTestSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.test.tsx',
    );
    const composerHookTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/hooks/useConversationComposer.test.ts',
    );
    const layoutHookTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/hooks/useConversationLayoutState.test.ts',
    );
    const advisorContextDerivationTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/hooks/useAdvisorContextDerivation.test.ts',
    );
    const panelTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ConversationPanels.test.tsx',
    );
    const expertControlsTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ConversationExpertControls.test.tsx',
    );
    const composerShellTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ConversationComposerShell.test.tsx',
    );
    const messageListShellTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ConversationMessageListShell.test.tsx',
    );
    const upgradeBannerTestSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ConversationUpgradeBanner.test.tsx',
    );
    const contractTestSource = readRepoFile('frontend-nextjs/features/conversation/contracts.test.ts');
    const combinedTestSource = `${guidanceCardTestSource}\n${conversationHistoryAdapterTestSource}\n${conversationSessionBootstrapTestSource}\n${conversationActionHandlersTestSource}\n${conversationLocalPersistenceTestSource}\n${conversationChatTestSource}\n${composerHookTestSource}\n${layoutHookTestSource}\n${advisorContextDerivationTestSource}\n${panelTestSource}\n${expertControlsTestSource}\n${composerShellTestSource}\n${messageListShellTestSource}\n${upgradeBannerTestSource}\n${contractTestSource}`;

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
    const messageListShellSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/MessageListShell.tsx',
    );
    const rendererSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/MessageCardRenderer.tsx',
    );

    expect(conversationChatSource).not.toContain("from '@/features/conversation/components/MessageCardRenderer'");
    expect(messageListShellSource).toContain("from '@/features/conversation/components/MessageCardRenderer'");
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

  it('keeps conversation layout state in the feature hook layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const layoutHookSource = readRepoFile(
      'frontend-nextjs/features/conversation/hooks/useConversationLayoutState.ts',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/hooks/useConversationLayoutState'");
    expect(layoutHookSource).toContain('export function useConversationLayoutState');
    expect(layoutHookSource).toContain('toggleBriefPinnedOpen');
    expect(layoutHookSource).toContain('updateContextPanePercentFromPointer');
    expect(layoutHookSource).toContain('finishContextResize');
  });

  it('keeps conversation panels in the feature component layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const visualBriefPanelSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/VisualBriefPanel.tsx',
    );
    const advisorContextPanelSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/AdvisorContextPanel.tsx',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/components/VisualBriefPanel'");
    expect(conversationChatSource).toContain("from '@/features/conversation/components/AdvisorContextPanel'");
    expect(conversationChatSource).not.toContain('空间 VisualBrief ·');
    expect(conversationChatSource).not.toContain('拖动调整上下文和聊天窗口高度');
    expect(visualBriefPanelSource).toContain('export function VisualBriefPanel');
    expect(advisorContextPanelSource).toContain('export function AdvisorContextPanel');
  });

  it('keeps expert controls in the feature component layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const expertControlsSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ExpertControls.tsx',
    );
    const composerShellSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ComposerShell.tsx',
    );

    expect(conversationChatSource).not.toContain('aria-label="选择专家视角"');
    expect(conversationChatSource).not.toContain('aria-label="召集团队"');
    expect(composerShellSource).toContain("from '@/features/conversation/components/ExpertControls'");
    expect(expertControlsSource).toContain('export function ExpertControls');
    expect(expertControlsSource).toContain('选择专家视角');
    expect(expertControlsSource).toContain('召集团队');
  });

  it('keeps composer shell in the feature component layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const composerShellSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/ComposerShell.tsx',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/components/ComposerShell'");
    expect(conversationChatSource).not.toContain('aria-label="发送"');
    expect(conversationChatSource).not.toContain('ui-card-shell ui-card-shell-strong');
    expect(composerShellSource).toContain('export function ComposerShell');
    expect(composerShellSource).toContain('aria-label="发送"');
  });

  it('keeps message list shell in the feature component layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const messageListShellSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/MessageListShell.tsx',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/components/MessageListShell'");
    expect(conversationChatSource).not.toContain('随时开始聊');
    expect(conversationChatSource).not.toContain('function TypingIndicator');
    expect(messageListShellSource).toContain('export function MessageListShell');
    expect(messageListShellSource).toContain('随时开始聊');
    expect(messageListShellSource).toContain('MessageCardRenderer');
  });

  it('keeps upgrade banner in the feature component layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const upgradeBannerSource = readRepoFile(
      'frontend-nextjs/features/conversation/components/UpgradeBanner.tsx',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/components/UpgradeBanner'");
    expect(conversationChatSource).not.toContain('对话已积累足够上下文，可以整理为正式项目');
    expect(conversationChatSource).not.toContain('立即整理');
    expect(upgradeBannerSource).toContain('export function UpgradeBanner');
    expect(upgradeBannerSource).toContain('对话已积累足够上下文，可以整理为正式项目');
  });

  it('keeps ConversationChat free of disabled legacy advisor context blocks', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );

    expect(conversationChatSource).not.toContain('{false &&');
    expect(conversationChatSource).not.toContain("handleAdvisorPrompt('deep-dive')");
    expect(conversationChatSource).not.toContain('advisorClosingLine');
  });

  it('keeps advisor context derivation in the feature hook layer', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const advisorContextDerivationSource = readRepoFile(
      'frontend-nextjs/features/conversation/hooks/useAdvisorContextDerivation.ts',
    );

    expect(conversationChatSource).toContain("from '@/features/conversation/hooks/useAdvisorContextDerivation'");
    expect(conversationChatSource).not.toContain(".split('\\n')");
    expect(conversationChatSource).not.toContain('advisorSuggestionLines');
    expect(advisorContextDerivationSource).toContain('export function useAdvisorContextDerivation');
    expect(advisorContextDerivationSource).toContain('advisorInsightLines');
  });

  it('keeps ConversationChat as the final composition shell', () => {
    const conversationChatSource = readRepoFile(
      'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    );
    const conversationChatLines = conversationChatSource.split('\n');
    const requiredCompositionImports = [
      "from '@/features/conversation/components/AdvisorContextPanel'",
      "from '@/features/conversation/components/ComposerShell'",
      "from '@/features/conversation/components/MessageListShell'",
      "from '@/features/conversation/components/UpgradeBanner'",
      "from '@/features/conversation/components/VisualBriefPanel'",
      "from '@/features/conversation/hooks/useAdvisorContextDerivation'",
      "from '@/features/conversation/hooks/useConversationComposer'",
      "from '@/features/conversation/hooks/useConversationLayoutState'",
    ];

    expect(CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT.currentVersion).toBe(
      'v1.7-conversation-local-persistence-extracted',
    );
    expect(conversationChatLines.length).toBeLessThanOrEqual(220);
    for (const importPath of requiredCompositionImports) {
      expect(conversationChatSource).toContain(importPath);
    }
    expect(conversationChatSource).not.toContain('function TypingIndicator');
    expect(conversationChatSource).not.toContain('function SchemeVersionSelectionCard');
    expect(conversationChatSource).not.toContain('对话已积累足够上下文，可以整理为正式项目');
    expect(conversationChatSource).not.toContain('随时开始聊');
    expect(conversationChatSource).not.toContain(".split('\\n')");
  });

  it('keeps analysis page conversation history adaptation in the feature layer', () => {
    const analysisPageSource = readRepoFile(
      'frontend-nextjs/app/analysis/[sessionId]/page.tsx',
    );
    const historyAdapterSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationHistoryAdapter.ts',
    );

    expect(analysisPageSource).toContain("from '@/features/conversation/conversationHistoryAdapter'");
    expect(analysisPageSource).not.toContain('const buildConversationMessagesFromHistory =');
    expect(analysisPageSource).not.toContain('const hydrateMissingGuidanceCards =');
    expect(analysisPageSource).not.toContain('const resolveGuidanceSelectionLabel =');
    expect(historyAdapterSource).toContain('export const EMPTY_CHAT_MESSAGES');
    expect(historyAdapterSource).toContain('export function buildConversationMessagesFromHistory');
    expect(historyAdapterSource).toContain('export function hydrateMissingGuidanceCards');
  });

  it('keeps analysis page conversation session bootstrap in the feature layer', () => {
    const analysisPageSource = readRepoFile(
      'frontend-nextjs/app/analysis/[sessionId]/page.tsx',
    );
    const sessionBootstrapSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationSessionBootstrap.ts',
    );

    expect(analysisPageSource).toContain("from '@/features/conversation/conversationSessionBootstrap'");
    expect(analysisPageSource).not.toContain('sessionStorage.getItem(`conv_init_');
    expect(analysisPageSource).not.toContain('JSON.parse(initRaw)');
    expect(analysisPageSource).not.toContain('hydrateMissingGuidanceCards(');
    expect(sessionBootstrapSource).toContain('export async function bootstrapConversationSession');
  });

  it('keeps analysis page conversation send and card response actions in the feature layer', () => {
    const analysisPageSource = readRepoFile(
      'frontend-nextjs/app/analysis/[sessionId]/page.tsx',
    );
    const actionHandlersSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationActionHandlers.ts',
    );

    expect(analysisPageSource).toContain("from '@/features/conversation/conversationActionHandlers'");
    expect(analysisPageSource).not.toContain('api.sendConversationMessage(');
    expect(analysisPageSource).not.toContain('[专家视角设定]');
    expect(analysisPageSource).not.toContain('[card:${optionId}]');
    expect(analysisPageSource).not.toContain('card_responded: true');
    expect(actionHandlersSource).toContain('export async function sendConversationMessageAction');
    expect(actionHandlersSource).toContain('export async function respondToGuidanceCardAction');
  });

  it('keeps advisor conversation local persistence in the feature layer', () => {
    const analysisPageSource = readRepoFile(
      'frontend-nextjs/app/analysis/[sessionId]/page.tsx',
    );
    const localPersistenceSource = readRepoFile(
      'frontend-nextjs/features/conversation/conversationLocalPersistence.ts',
    );

    expect(analysisPageSource).toContain("from '@/features/conversation/conversationLocalPersistence'");
    expect(analysisPageSource).not.toContain('ADVISOR_CONVERSATION_STORAGE_KEY');
    expect(analysisPageSource).not.toContain('analysis.advisor.conversations.v1');
    expect(analysisPageSource).not.toContain('setConversationMessagesByScene(parsed)');
    expect(localPersistenceSource).toContain('export function restoreAdvisorConversationMessages');
    expect(localPersistenceSource).toContain('export function persistAdvisorConversationMessages');
  });
});
