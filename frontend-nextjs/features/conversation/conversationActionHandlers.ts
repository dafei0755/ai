import type { SetStateAction } from 'react';

import type {
  AdvisorSceneContext,
  ChatMessage,
  GuidanceCardStructuredResponse,
} from './types';

type ConversationResponse = {
  reply?: string | null;
  upgrade_suggested?: boolean;
  upgrade_signal?: Record<string, unknown> | null;
  guidance_card?: Record<string, unknown> | null;
};

type SendConversationMessage = (
  sessionId: string,
  message: string,
  cardResponse?: {
    in_response_to_card_id?: string;
    selected_option_id?: string;
    card_response?: unknown;
  },
  context?: { expert_perspective?: string },
) => Promise<ConversationResponse>;

type SetMessages = (updater: SetStateAction<ChatMessage[]>) => void;
type CreateId = (prefix: 'user' | 'ai') => string;
type UpgradeIndicators = {
  freeze_readiness: number;
  cognitive_debt: number;
  diverge_fatigue: number;
};

type BaseConversationActionOptions = {
  sessionId: string;
  systemMode: string;
  activeExpertPerspective: string;
  advisorSceneContext: AdvisorSceneContext;
  setMessages: SetMessages;
  sendConversationMessage: SendConversationMessage;
  now?: () => string;
  createId?: CreateId;
  onError?: (error: unknown) => void;
};

export type SendConversationMessageActionOptions = BaseConversationActionOptions & {
  text: string;
  boardVisualBriefPrompt?: string | null;
  setUpgradeIndicators?: (indicators: UpgradeIndicators) => void;
  setUpgradeSuggestionText?: (text: string) => void;
  setShowUpgradeBanner?: (visible: boolean) => void;
};

export type RespondToGuidanceCardActionOptions = BaseConversationActionOptions & {
  cardId: string;
  optionId?: string;
  freetext?: string;
  structuredResponse?: GuidanceCardStructuredResponse;
};

const defaultNow = () => new Date().toISOString();
const defaultCreateId: CreateId = (prefix) => `${prefix}-${Date.now()}`;

const buildPerspectivePrefix = (
  systemMode: string,
  advisorSceneContext: AdvisorSceneContext,
  activeExpertPerspective: string,
) => {
  if (systemMode === 'conversation') return '';
  return `[专家视角设定]\n当前场景：${advisorSceneContext.label}\n当前指定视角：${activeExpertPerspective}\n回答时请围绕该视角深挖关键判断、风险取舍与执行动作。\n\n`;
};

const buildScenePrefix = (
  systemMode: string,
  advisorSceneContext: AdvisorSceneContext,
) => {
  if (systemMode === 'conversation') return '';
  return `[当前左侧场景]\n场景：${advisorSceneContext.label}\n引用：${advisorSceneContext.sceneRef}\n系统上下文判断：\n${advisorSceneContext.suggestion}\n\n[用户本轮指令]\n`;
};

const buildVisualBriefPrefix = (boardVisualBriefPrompt?: string | null) => {
  if (!boardVisualBriefPrompt) return '';
  return `[方案画布空间 VisualBrief]\n${boardVisualBriefPrompt}\n\n[用户本轮指令]\n`;
};

const isUpgradeIndicators = (value: unknown): value is UpgradeIndicators => {
  if (!value || typeof value !== 'object') return false;
  const indicators = value as Partial<UpgradeIndicators>;
  return (
    typeof indicators.freeze_readiness === 'number' &&
    typeof indicators.cognitive_debt === 'number' &&
    typeof indicators.diverge_fatigue === 'number'
  );
};

const appendAssistantReply = ({
  response,
  setMessages,
  now,
  createId,
}: {
  response: ConversationResponse;
  setMessages: SetMessages;
  now: () => string;
  createId: CreateId;
}) => {
  if (!response.reply) return;
  const aiMessage: ChatMessage = {
    id: createId('ai'),
    role: 'assistant',
    content: response.reply,
    timestamp: now(),
    guidance_card: response.guidance_card as ChatMessage['guidance_card'] | undefined,
  };
  setMessages((prev) => [...prev, aiMessage]);
};

const resolveGuidanceSelectionLabel = (
  card: ChatMessage['guidance_card'] | undefined,
  optionId?: string,
  freetext?: string,
) => {
  if (freetext) return freetext;
  if (!card || !optionId) return undefined;
  const allOptions = [
    ...(card.options ?? []),
    ...(card.pages ?? []).flatMap((page) => page.options ?? []),
    ...(card.version_cards ?? []).map((version) => ({
      id: version.id,
      label: version.name,
      description: version.subtitle,
    })),
  ];
  const option = allOptions.find((item) => item.id === optionId);
  if (!option) return optionId;
  return option.description ? `${option.label}：${option.description}` : option.label;
};

export const markGuidanceCardResponded = (
  messages: ChatMessage[],
  cardId: string,
  optionId?: string,
  freetext?: string,
): ChatMessage[] =>
  messages.map((message) => {
    if (message.guidance_card?.card_id !== cardId) return message;
    return {
      ...message,
      card_responded: true,
      card_selection_label: resolveGuidanceSelectionLabel(
        message.guidance_card,
        optionId,
        freetext,
      ),
    };
  });

export async function sendConversationMessageAction({
  sessionId,
  text,
  systemMode,
  activeExpertPerspective,
  advisorSceneContext,
  boardVisualBriefPrompt,
  setMessages,
  sendConversationMessage,
  setUpgradeIndicators,
  setUpgradeSuggestionText,
  setShowUpgradeBanner,
  now = defaultNow,
  createId = defaultCreateId,
  onError,
}: SendConversationMessageActionOptions): Promise<void> {
  const userMessage: ChatMessage = {
    id: createId('user'),
    role: 'user',
    content: text,
    timestamp: now(),
  };
  setMessages((prev) => [...prev, userMessage]);

  try {
    const response = await sendConversationMessage(
      sessionId,
      `${buildPerspectivePrefix(systemMode, advisorSceneContext, activeExpertPerspective)}${buildScenePrefix(systemMode, advisorSceneContext)}${buildVisualBriefPrefix(boardVisualBriefPrompt)}${text}`,
      undefined,
      { expert_perspective: activeExpertPerspective },
    );

    appendAssistantReply({ response, setMessages, now, createId });

    if (response.upgrade_suggested && response.upgrade_signal) {
      const signal = response.upgrade_signal;
      if (isUpgradeIndicators(signal.indicators)) setUpgradeIndicators?.(signal.indicators);
      if (typeof signal.suggestion_text === 'string') {
        setUpgradeSuggestionText?.(signal.suggestion_text);
      }
      setShowUpgradeBanner?.(true);
    }
  } catch (error) {
    onError?.(error);
  }
}

export async function respondToGuidanceCardAction({
  sessionId,
  cardId,
  optionId,
  freetext,
  structuredResponse,
  systemMode,
  activeExpertPerspective,
  advisorSceneContext,
  setMessages,
  sendConversationMessage,
  now = defaultNow,
  createId = defaultCreateId,
  onError,
}: RespondToGuidanceCardActionOptions): Promise<void> {
  setMessages((prev) => markGuidanceCardResponded(prev, cardId, optionId, freetext));
  const text = freetext || (optionId ? `[card:${optionId}]` : '[skip]');

  try {
    const response = await sendConversationMessage(
      sessionId,
      `${buildPerspectivePrefix(systemMode, advisorSceneContext, activeExpertPerspective)}${text}`,
      {
        in_response_to_card_id: cardId,
        selected_option_id: optionId,
        card_response: structuredResponse,
      },
      { expert_perspective: activeExpertPerspective },
    );

    appendAssistantReply({ response, setMessages, now, createId });
  } catch (error) {
    onError?.(error);
  }
}
