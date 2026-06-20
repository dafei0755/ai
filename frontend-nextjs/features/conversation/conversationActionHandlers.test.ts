import {
  respondToGuidanceCardAction,
  sendConversationMessageAction,
} from './conversationActionHandlers';
import type { SetStateAction } from 'react';
import type { ChatMessage, GuidanceCardStructuredResponse } from './types';

const createMessageState = (initial: ChatMessage[] = []) => {
  let messages = initial;
  const setMessages = jest.fn((updater: SetStateAction<ChatMessage[]>) => {
    messages = typeof updater === 'function'
      ? (updater as (value: ChatMessage[]) => ChatMessage[])(messages)
      : updater;
  });

  return {
    setMessages,
    getMessages: () => messages,
  };
};

describe('conversationActionHandlers', () => {
  it('sends scene-aware conversation prompts, appends the reply, and surfaces upgrade signals', async () => {
    const state = createMessageState();
    const sendConversationMessage = jest.fn(async () => ({
      reply: 'Use the courtyard as the emotional anchor.',
      guidance_card: {
        card_id: 'next-card',
        card_type: 'demand_reconstruction_blueprint',
        prompt_text: 'Next decision',
        options: [],
      },
      upgrade_suggested: true,
      upgrade_signal: {
        indicators: {
          freeze_readiness: 0.8,
          cognitive_debt: 0.4,
          diverge_fatigue: 0.2,
        },
        suggestion_text: 'Ready to upgrade',
      },
    }));
    const setUpgradeIndicators = jest.fn();
    const setUpgradeSuggestionText = jest.fn();
    const setShowUpgradeBanner = jest.fn();

    await sendConversationMessageAction({
      sessionId: 'conv-123',
      text: 'How should I balance old and new?',
      systemMode: 'project',
      activeExpertPerspective: '实施边界视角',
      advisorSceneContext: {
        key: 'project::board',
        label: '方案画布',
        sceneRef: 'board',
        suggestion: 'Focus on constructability.',
      },
      boardVisualBriefPrompt: 'Visual brief content',
      setMessages: state.setMessages,
      sendConversationMessage,
      setUpgradeIndicators,
      setUpgradeSuggestionText,
      setShowUpgradeBanner,
      now: () => '2026-06-20T00:00:00.000Z',
      createId: (prefix) => `${prefix}-fixed`,
      onError: jest.fn(),
    });

    expect(sendConversationMessage).toHaveBeenCalledWith(
      'conv-123',
      expect.stringContaining('[专家视角设定]'),
      undefined,
      { expert_perspective: '实施边界视角' },
    );
    const sentPrompt = (sendConversationMessage.mock.calls[0] as unknown[])[1] as string;
    expect(sentPrompt).toContain('[当前左侧场景]');
    expect(sentPrompt).toContain('[方案画布空间 VisualBrief]');
    expect(sentPrompt).toContain('How should I balance old and new?');
    expect(state.getMessages()).toEqual([
      {
        id: 'user-fixed',
        role: 'user',
        content: 'How should I balance old and new?',
        timestamp: '2026-06-20T00:00:00.000Z',
      },
      {
        id: 'ai-fixed',
        role: 'assistant',
        content: 'Use the courtyard as the emotional anchor.',
        timestamp: '2026-06-20T00:00:00.000Z',
        guidance_card: {
          card_id: 'next-card',
          card_type: 'demand_reconstruction_blueprint',
          prompt_text: 'Next decision',
          options: [],
        },
      },
    ]);
    expect(setUpgradeIndicators).toHaveBeenCalledWith({
      freeze_readiness: 0.8,
      cognitive_debt: 0.4,
      diverge_fatigue: 0.2,
    });
    expect(setUpgradeSuggestionText).toHaveBeenCalledWith('Ready to upgrade');
    expect(setShowUpgradeBanner).toHaveBeenCalledWith(true);
  });

  it('marks guidance cards responded, sends structured card responses, and appends the reply', async () => {
    const structuredResponse: GuidanceCardStructuredResponse = {
      pages: [
        {
          page_index: 0,
          page_title: 'Version',
          response_mode: 'single_select',
          selected_option_id: 'standard',
        },
      ],
    };
    const state = createMessageState([
      {
        id: 'assistant-card',
        role: 'assistant',
        content: 'Choose a version',
        timestamp: '2026-06-20T00:00:00.000Z',
        guidance_card: {
          card_id: 'version-card',
          card_type: 'scheme_version_selection',
          prompt_text: 'Choose a version',
          options: [],
          version_cards: [
            {
              id: 'standard',
              name: '标准版',
              subtitle: '解决能不能成立',
            },
          ],
        },
      },
    ]);
    const sendConversationMessage = jest.fn(async () => ({
      reply: 'Continue with the standard version.',
      upgrade_suggested: false,
      upgrade_signal: null,
    }));

    await respondToGuidanceCardAction({
      sessionId: 'conv-123',
      cardId: 'version-card',
      optionId: 'standard',
      structuredResponse,
      systemMode: 'project',
      activeExpertPerspective: '平衡推进视角',
      advisorSceneContext: {
        key: 'project::board',
        label: '方案画布',
        sceneRef: 'board',
        suggestion: 'Focus on constructability.',
      },
      setMessages: state.setMessages,
      sendConversationMessage,
      now: () => '2026-06-20T00:01:00.000Z',
      createId: (prefix) => `${prefix}-reply`,
      onError: jest.fn(),
    });

    expect(state.getMessages()[0]).toMatchObject({
      card_responded: true,
      card_selection_label: '标准版：解决能不能成立',
    });
    expect(sendConversationMessage).toHaveBeenCalledWith(
      'conv-123',
      expect.stringContaining('[card:standard]'),
      {
        in_response_to_card_id: 'version-card',
        selected_option_id: 'standard',
        card_response: structuredResponse,
      },
      { expert_perspective: '平衡推进视角' },
    );
    expect(state.getMessages()[1]).toMatchObject({
      id: 'ai-reply',
      role: 'assistant',
      content: 'Continue with the standard version.',
    });
  });
});
